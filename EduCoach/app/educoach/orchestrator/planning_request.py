"""Typed, request-local planning constraints from explicit user language."""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, time
from decimal import Decimal, InvalidOperation
from enum import StrEnum
import re

from educoach.models import AvailabilityType, StudyTask, TaskType
from educoach.rules import RuleSeverity, RuleViolation
from educoach.services import LearnerMemorySnapshot
from educoach.validators.repetition import normalize_response_text
from educoach.writeback import StudyPlanWriteProposal


class RequestConstraintSource(StrEnum):
    CURRENT_MESSAGE = "current_message"


class ConstraintStrength(StrEnum):
    HARD = "hard"
    SOFT = "soft"


class RecurringDayScope(StrEnum):
    WEEKDAY = "weekday"


class ScheduleAnchorType(StrEnum):
    HOME_ARRIVAL = "home_arrival"


class AvailabilityImplication(StrEnum):
    NONE = "none"


@dataclass(frozen=True)
class DailySubjectLimit:
    area_type: str
    area_code: str
    max_minutes_per_day: int
    strength: ConstraintStrength = ConstraintStrength.HARD
    source: RequestConstraintSource = RequestConstraintSource.CURRENT_MESSAGE

    def __post_init__(self) -> None:
        if not self.area_type or not self.area_code:
            raise ValueError("daily subject limit requires an area")
        if self.max_minutes_per_day < 1:
            raise ValueError("daily subject limit must be positive")
        if self.strength is not ConstraintStrength.HARD:
            raise ValueError("daily subject limit must be hard")


@dataclass(frozen=True)
class SessionTolerance:
    preferred_max_continuous_minutes: int
    strength: ConstraintStrength = ConstraintStrength.SOFT
    source: RequestConstraintSource = RequestConstraintSource.CURRENT_MESSAGE

    def __post_init__(self) -> None:
        if self.preferred_max_continuous_minutes < 1:
            raise ValueError("session tolerance must be positive")
        if self.strength is not ConstraintStrength.SOFT:
            raise ValueError("session tolerance must be soft")


@dataclass(frozen=True)
class RecurringCommitmentSummary:
    subject: str
    occurrence_count: int
    day_scope: RecurringDayScope
    exact_days: tuple[str, ...] = ()
    source: RequestConstraintSource = RequestConstraintSource.CURRENT_MESSAGE

    def __post_init__(self) -> None:
        if not self.subject or self.occurrence_count < 1:
            raise ValueError("recurring commitment requires a subject and count")
        if self.exact_days:
            raise ValueError("unresolved recurring commitment cannot contain exact days")


@dataclass(frozen=True)
class ScheduleAnchor:
    anchor_type: ScheduleAnchorType
    anchor_time: time
    availability_implication: AvailabilityImplication = AvailabilityImplication.NONE
    source: RequestConstraintSource = RequestConstraintSource.CURRENT_MESSAGE

    def __post_init__(self) -> None:
        if self.availability_implication is not AvailabilityImplication.NONE:
            raise ValueError("schedule anchor cannot imply availability")


@dataclass(frozen=True)
class PlanningRequestContext:
    daily_subject_limits: tuple[DailySubjectLimit, ...] = ()
    session_tolerances: tuple[SessionTolerance, ...] = ()
    recurring_commitments: tuple[RecurringCommitmentSummary, ...] = ()
    schedule_anchors: tuple[ScheduleAnchor, ...] = ()

    @property
    def is_empty(self) -> bool:
        return not any(
            (
                self.daily_subject_limits,
                self.session_tolerances,
                self.recurring_commitments,
                self.schedule_anchors,
            )
        )


@dataclass(frozen=True)
class DailyWorkloadClaim:
    min_minutes_per_day: int
    max_minutes_per_day: int

    def __post_init__(self) -> None:
        if self.min_minutes_per_day < 1:
            raise ValueError("daily workload minimum must be positive")
        if self.max_minutes_per_day < self.min_minutes_per_day:
            raise ValueError("daily workload range is invalid")


class PlanningClaimKind(StrEnum):
    EXACT_CLOCK_ASSIGNMENT = "exact_clock_assignment"
    DAILY_WORKLOAD_ASSIGNMENT = "daily_workload_assignment"


class PlanningClaimModality(StrEnum):
    ASSERTED = "asserted"
    CONDITIONAL = "conditional"
    ILLUSTRATIVE = "illustrative"
    REPORTED = "reported"


@dataclass(frozen=True)
class PlanningClaim:
    kind: PlanningClaimKind
    modality: PlanningClaimModality
    start_time: time | None = None
    end_time: time | None = None
    min_minutes_per_day: int | None = None
    max_minutes_per_day: int | None = None
    is_capacity_prescription: bool = False

    def __post_init__(self) -> None:
        if self.kind is PlanningClaimKind.EXACT_CLOCK_ASSIGNMENT:
            if self.start_time is None or self.end_time is None:
                raise ValueError("exact clock assignment requires start and end times")
            if (
                self.min_minutes_per_day is not None
                or self.max_minutes_per_day is not None
            ):
                raise ValueError("exact clock assignment cannot contain workload")
            return
        if self.start_time is not None or self.end_time is not None:
            raise ValueError("daily workload assignment cannot contain clock times")
        if (
            self.min_minutes_per_day is None
            or self.max_minutes_per_day is None
            or self.min_minutes_per_day < 1
            or self.max_minutes_per_day < self.min_minutes_per_day
        ):
            raise ValueError("daily workload assignment requires a valid range")


_SUBJECT_LIMIT_PATTERNS = (
    re.compile(
        r"\bmatematige\s+gunde\s+en\s+fazla\s+"
        r"(?P<value>\d{1,3})\s*(?P<unit>saat|dakika)\s+ayirabilirim\b"
    ),
    re.compile(
        r"\ben\s+fazla\s+gunde\s+"
        r"(?P<value>\d{1,3})\s*(?P<unit>saat|dakika)\s+"
        r"matematik\s+calisabilirim\b"
    ),
)
_SESSION_TOLERANCE_PATTERNS = (
    re.compile(
        r"\b(?P<value>\d{1,3})\s*(?P<unit>saat|dakika)\s+"
        r"sonra\s+sikiliyorum\b"
    ),
    re.compile(
        r"\b(?P<value>\d{1,3})\s*(?P<unit>saat|dakika)\s+"
        r"calisinca\s+sikiliyorum\b"
    ),
)
_RECURRING_COMMITMENT_PATTERNS = (
    re.compile(
        r"\bhaftada\s+(?P<count>\d{1,2}|uc)\s+"
        r"hafta\s+i{1,2}ci\s+gunu\s+ingilizce\s+kursum\s+var\b"
    ),
    re.compile(
        r"\bhafta\s+i{1,2}ci\s+(?P<count>\d{1,2}|uc)\s+gun\s+"
        r"ingilizce\s+kursum\s+var\b"
    ),
)
_HOME_ARRIVAL_PATTERNS = (
    re.compile(
        r"\beve\s+(?P<hour>[01]?\d|2[0-3]):(?P<minute>[0-5]\d)"
        r"(?:['’]?de)?\s+geliyorum\b"
    ),
    re.compile(
        r"\baksam\s+saat\s+(?P<hour>0?[1-9]|1[01])"
        r"(?:['’]?te|\s+te)\s+eve\s+geliyorum\b"
    ),
)
_NUMERIC_DURATION_PATTERN = re.compile(
    r"(?<![\d:])(?P<minimum>\d{1,3}(?:[.,]\d+)?)"
    r"(?:\s*[-–—]\s*(?P<maximum>\d{1,3}(?:[.,]\d+)?))?\s*"
    r"(?P<unit>saat|dakika)(?:lik|dir|tir)?\b"
)
_DAILY_SCOPE_PATTERN = re.compile(r"\b(?:gunluk|gunde|her\s+gun)\b")
_TOTAL_WORKLOAD_CONTEXT_PATTERN = re.compile(r"\btoplam\b")
_CAPACITY_PRESCRIPTION_PATTERN = re.compile(
    r"\b(?:zorunlu(?:dur)?|sart(?:tir)?|calismali(?:sin|siniz)|"
    r"calisma(?:n|niz)\s+gerekir)\b"
)
_BREAK_BEFORE_DURATION_PATTERN = re.compile(
    r"\b(?:mola|ara|dinlenme)\w*\s*(?:icin\s*)?$"
)
_BREAK_AFTER_DURATION_PATTERN = re.compile(
    r"^\s*(?:lik\s+)?(?:mola|ara|dinlenme)\w*\b"
)
_CLOCK_RANGE_PATTERN = re.compile(
    r"(?<!\d)(?P<start_hour>[01]?\d|2[0-3])[:.]?"
    r"(?P<start_minute>[0-5]\d)\s*[-–—]\s*"
    r"(?P<end_hour>[01]?\d|2[0-3])[:.]?"
    r"(?P<end_minute>[0-5]\d)(?!\d)"
)
_STUDY_ACTIVITY_PATTERN = re.compile(
    r"\b(?:calis|ders|odev|tyt|ayt|yks|hazirlik|matematik|fizik|kimya|"
    r"biyoloji|turkce|sosyal|ingilizce|konu|soru|test|tekrar|pratik|"
    r"okuma)\w*\b"
)
_STUDY_ACTION_PATTERN = re.compile(
    r"\b(?:calis|coz|yap|tamamla|tekrar\s+et|oku|incele)\w*\b"
)
_CONDITIONAL_CLAIM_PATTERN = re.compile(
    r"\b(?:eger|musait|uygunsa|vaktin\s+varsa|vaktiniz\s+varsa|"
    r"ayirabilirsen|netlesirse|netlestiginde|olursa)\w*\b"
)
_ILLUSTRATIVE_CLAIM_PATTERN = re.compile(
    r"\b(?:ornegin|mesela|bazi\s+ogrenciler|bir\s+ogrencinin|"
    r"dusunulebilir)\b"
)
_REPORTED_CLAIM_PATTERN = re.compile(
    r"\b(?:su\s+anda|gecen\s+yil|dun|soyledin|soyledigin|"
    r"calistigini|calisiyordun|calisiyordunuz)\b"
)
_CONSTRAINED_AREA_DESCRIPTION_PATTERNS = {
    ("subject", "mathematics"): re.compile(r"\bmatematik\w*\b"),
}
_CONTENT_BEARING_TASK_TYPES = frozenset(
    {
        TaskType.STUDY,
        TaskType.PRACTICE,
        TaskType.REVISION,
        TaskType.READING,
        TaskType.VOCABULARY,
        TaskType.HOMEWORK,
    }
)


def extract_planning_request_context(message: str) -> PlanningRequestContext:
    """Extract only the deliberately small set of explicit planning forms."""

    normalized = normalize_response_text(message)

    subject_limits = tuple(
        DailySubjectLimit(
            area_type="subject",
            area_code="mathematics",
            max_minutes_per_day=_to_minutes(
                int(match.group("value")), match.group("unit")
            ),
        )
        for match in _find_matches(_SUBJECT_LIMIT_PATTERNS, normalized)
    )
    tolerances = tuple(
        SessionTolerance(
            preferred_max_continuous_minutes=_to_minutes(
                int(match.group("value")), match.group("unit")
            )
        )
        for match in _find_matches(_SESSION_TOLERANCE_PATTERNS, normalized)
    )
    commitments = tuple(
        RecurringCommitmentSummary(
            subject="english_course",
            occurrence_count=(
                3 if match.group("count") == "uc" else int(match.group("count"))
            ),
            day_scope=RecurringDayScope.WEEKDAY,
        )
        for match in _find_matches(_RECURRING_COMMITMENT_PATTERNS, normalized)
    )
    anchors = tuple(
        ScheduleAnchor(
            anchor_type=ScheduleAnchorType.HOME_ARRIVAL,
            anchor_time=_home_arrival_time(match),
        )
        for match in _find_matches(_HOME_ARRIVAL_PATTERNS, normalized)
    )
    return PlanningRequestContext(
        daily_subject_limits=subject_limits,
        session_tolerances=tolerances,
        recurring_commitments=commitments,
        schedule_anchors=anchors,
    )


def render_planning_request_context(context: PlanningRequestContext) -> str:
    """Render canonical system-owned context without repeating raw user text."""

    if context.is_empty:
        return ""

    lines = ["Planning request constraints:"]
    lines.extend(
        "- "
        f"{item.area_type}/{item.area_code} max "
        f"{item.max_minutes_per_day} min/day [HARD; CURRENT_MESSAGE]"
        for item in context.daily_subject_limits
    )
    lines.extend(
        "- preferred continuous session max "
        f"{item.preferred_max_continuous_minutes} min "
        "[SOFT; CURRENT_MESSAGE; not a daily-total limit]"
        for item in context.session_tolerances
    )
    lines.extend(
        "- recurring "
        f"{item.subject}: {item.occurrence_count} WEEKDAY occurrences/week; "
        "exact days UNKNOWN"
        for item in context.recurring_commitments
    )
    lines.extend(
        "- home arrival: "
        f"{item.anchor_time.strftime('%H:%M')}; availability implication NONE"
        for item in context.schedule_anchors
    )
    return "\n".join(lines)


def evaluate_request_subject_limits(
    context: PlanningRequestContext,
    proposal: StudyPlanWriteProposal,
) -> tuple[RuleViolation, ...]:
    """Evaluate hard per-subject limits independently of availability."""

    violations: list[RuleViolation] = []
    if context.daily_subject_limits and any(
        task.task_type in _CONTENT_BEARING_TASK_TYPES
        and (
            task.area_type is None
            or task.area_code is None
            or any(
                _task_description_contradicts_limit(task, limit)
                for limit in context.daily_subject_limits
            )
        )
        for task in proposal.tasks
    ):
        violations.append(
            RuleViolation(
                rule_id="PLAN_REQUEST_SUBJECT_LIMIT_UNVERIFIABLE",
                severity=RuleSeverity.ERROR,
                message=(
                    "A content-bearing task is missing canonical area metadata, "
                    "so the hard subject limit cannot be verified."
                ),
            )
        )
    for limit in context.daily_subject_limits:
        totals: defaultdict[date, int] = defaultdict(int)
        for task in proposal.tasks:
            if (
                task.area_type == limit.area_type
                and task.area_code == limit.area_code
            ):
                totals[task.task_date] += task.planned_minutes
        for target_date in sorted(totals):
            planned_minutes = totals[target_date]
            if planned_minutes <= limit.max_minutes_per_day:
                continue
            violations.append(
                RuleViolation(
                    rule_id="PLAN_REQUEST_SUBJECT_DAILY_LIMIT",
                    severity=RuleSeverity.ERROR,
                    message=(
                        f"Planned {planned_minutes} minutes for "
                        f"{limit.area_code} exceeds the request limit of "
                        f"{limit.max_minutes_per_day} minutes for "
                        f"{target_date.isoformat()}."
                    ),
                )
            )
    return tuple(violations)


def extract_daily_workload_claim(text: str) -> DailyWorkloadClaim | None:
    """Return the first asserted daily workload for compatibility callers."""

    claims = tuple(
        claim
        for claim in extract_response_planning_claims(text)
        if claim.kind is PlanningClaimKind.DAILY_WORKLOAD_ASSIGNMENT
        and claim.modality is PlanningClaimModality.ASSERTED
    )
    if not claims:
        return None
    claim = claims[0]
    assert claim.min_minutes_per_day is not None
    assert claim.max_minutes_per_day is not None
    return DailyWorkloadClaim(
        min_minutes_per_day=claim.min_minutes_per_day,
        max_minutes_per_day=claim.max_minutes_per_day,
    )


def extract_response_planning_claims(text: str) -> tuple[PlanningClaim, ...]:
    """Extract deterministic planning claims from composable lexical primitives."""

    normalized = normalize_response_text(text)
    segments = _logical_segments(normalized)
    return (
        _extract_exact_clock_claims(segments)
        + _extract_daily_workload_claims(normalized, segments)
    )


def evaluate_response_schedule_grounding(
    response_text: str,
    planning_request: PlanningRequestContext,
    snapshot: LearnerMemorySnapshot,
    proposal: StudyPlanWriteProposal | None,
) -> tuple[RuleViolation, ...]:
    """Reject narrow, unsupported schedule assignments from request-local facts."""

    if any(
        record.availability_type == AvailabilityType.AVAILABLE
        for record in snapshot.availability
    ):
        return ()

    has_unresolved_home_arrival = any(
        anchor.anchor_type == ScheduleAnchorType.HOME_ARRIVAL
        and anchor.availability_implication == AvailabilityImplication.NONE
        for anchor in planning_request.schedule_anchors
    )
    claims = extract_response_planning_claims(response_text)
    unsupported_clock_schedule = (
        has_unresolved_home_arrival
        and any(
            claim.kind is PlanningClaimKind.EXACT_CLOCK_ASSIGNMENT
            and claim.modality is PlanningClaimModality.ASSERTED
            for claim in claims
        )
    )
    asserted_workloads = tuple(
        claim
        for claim in claims
        if claim.kind is PlanningClaimKind.DAILY_WORKLOAD_ASSIGNMENT
        and claim.modality is PlanningClaimModality.ASSERTED
    )
    unsupported_daily_workload = bool(asserted_workloads) and (
        proposal is None
        or any(claim.is_capacity_prescription for claim in asserted_workloads)
    )
    if not (unsupported_clock_schedule or unsupported_daily_workload):
        return ()
    return (
        RuleViolation(
            rule_id="PLAN_RESPONSE_UNSUPPORTED_AVAILABILITY",
            severity=RuleSeverity.ERROR,
            message=(
                "Response assigns a concrete study schedule without recorded "
                "availability support."
            ),
        ),
    )


def evaluate_response_proposal_workload(
    response_text: str,
    proposal: StudyPlanWriteProposal,
) -> tuple[RuleViolation, ...]:
    """Compare an explicit prose daily workload with proposal task totals."""

    claims = tuple(
        claim
        for claim in extract_response_planning_claims(response_text)
        if claim.kind is PlanningClaimKind.DAILY_WORKLOAD_ASSIGNMENT
        and claim.modality is PlanningClaimModality.ASSERTED
    )
    if not claims:
        return ()

    totals: defaultdict[date, int] = defaultdict(int)
    for task in proposal.tasks:
        totals[task.task_date] += task.planned_minutes
    if not totals or all(
        claim.min_minutes_per_day is not None
        and claim.max_minutes_per_day is not None
        and all(
            claim.min_minutes_per_day <= total <= claim.max_minutes_per_day
            for total in totals.values()
        )
        for claim in claims
    ):
        return ()
    return (
        RuleViolation(
            rule_id="PLAN_RESPONSE_PROPOSAL_WORKLOAD_MISMATCH",
            severity=RuleSeverity.ERROR,
            message=(
                "Explicit daily workload in the response does not match "
                "the structured proposal daily totals."
            ),
        ),
    )


def _extract_exact_clock_claims(
    segments: tuple[str, ...],
) -> tuple[PlanningClaim, ...]:
    claims: list[PlanningClaim] = []
    for index, segment in enumerate(segments):
        for clock_range in _CLOCK_RANGE_PATTERN.finditer(segment):
            context_parts = [segment]
            has_assignment = _STUDY_ACTIVITY_PATTERN.search(segment) is not None
            if _is_clock_only_segment(segment, clock_range):
                if index + 1 >= len(segments):
                    continue
                assignment = segments[index + 1]
                if (
                    _STUDY_ACTIVITY_PATTERN.search(assignment) is None
                    or _STUDY_ACTION_PATTERN.search(assignment) is None
                ):
                    continue
                context_parts.append(assignment)
                has_assignment = True
            if not has_assignment:
                continue
            if index > 0 and segments[index - 1].rstrip().endswith(":"):
                previous_modality = _planning_claim_modality(segments[index - 1])
                if previous_modality is not PlanningClaimModality.ASSERTED:
                    context_parts.insert(0, segments[index - 1])
            context = " ".join(context_parts)
            modality = _planning_claim_modality(context)
            if modality is None:
                continue
            claims.append(
                PlanningClaim(
                    kind=PlanningClaimKind.EXACT_CLOCK_ASSIGNMENT,
                    modality=modality,
                    start_time=time(
                        int(clock_range.group("start_hour")),
                        int(clock_range.group("start_minute")),
                    ),
                    end_time=time(
                        int(clock_range.group("end_hour")),
                        int(clock_range.group("end_minute")),
                    ),
                )
            )
    return tuple(claims)


def _extract_daily_workload_claims(
    normalized: str,
    segments: tuple[str, ...],
) -> tuple[PlanningClaim, ...]:
    claims: list[PlanningClaim] = []
    has_schedule_context = len(_CLOCK_RANGE_PATTERN.findall(normalized)) >= 2
    for segment in segments:
        for clause in _workload_clauses(segment):
            has_daily_scope = _DAILY_SCOPE_PATTERN.search(clause) is not None
            has_total_schedule_scope = (
                has_schedule_context
                and _TOTAL_WORKLOAD_CONTEXT_PATTERN.search(clause) is not None
            )
            if not (has_daily_scope or has_total_schedule_scope):
                continue
            modality = _planning_claim_modality(clause)
            if modality is None:
                continue
            for duration in _NUMERIC_DURATION_PATTERN.finditer(clause):
                if _is_break_duration(clause, duration):
                    continue
                minimum = _duration_to_minutes(
                    duration.group("minimum"), duration.group("unit")
                )
                maximum = _duration_to_minutes(
                    duration.group("maximum") or duration.group("minimum"),
                    duration.group("unit"),
                )
                if minimum is None or maximum is None:
                    continue
                claims.append(
                    PlanningClaim(
                        kind=PlanningClaimKind.DAILY_WORKLOAD_ASSIGNMENT,
                        modality=modality,
                        min_minutes_per_day=minimum,
                        max_minutes_per_day=maximum,
                        is_capacity_prescription=(
                            _CAPACITY_PRESCRIPTION_PATTERN.search(clause)
                            is not None
                        ),
                    )
                )
    return tuple(claims)


def _is_clock_only_segment(segment: str, clock_range: re.Match[str]) -> bool:
    remainder = segment[:clock_range.start()] + segment[clock_range.end():]
    return re.fullmatch(r"[\s:*_`#>\-]*", remainder) is not None


def _logical_segments(normalized: str) -> tuple[str, ...]:
    return tuple(
        segment.strip()
        for segment in re.split(r"(?<=[.!?])\s+|[\r\n]+", normalized)
        if re.search(r"\w", segment)
    )


def _workload_clauses(segment: str) -> tuple[str, ...]:
    return tuple(
        clause.strip()
        for clause in re.split(r"(?<!\d),(?!\d)|;", segment)
        if re.search(r"\w", clause)
    )


def _is_break_duration(segment: str, duration: re.Match[str]) -> bool:
    before = segment[max(0, duration.start() - 24):duration.start()]
    after = segment[duration.end():duration.end() + 24]
    return (
        _BREAK_BEFORE_DURATION_PATTERN.search(before) is not None
        or _BREAK_AFTER_DURATION_PATTERN.search(after) is not None
    )


def _planning_claim_modality(
    segment: str,
) -> PlanningClaimModality | None:
    if "?" in segment:
        return None
    if _CONDITIONAL_CLAIM_PATTERN.search(segment) is not None:
        return PlanningClaimModality.CONDITIONAL
    if _ILLUSTRATIVE_CLAIM_PATTERN.search(segment) is not None:
        return PlanningClaimModality.ILLUSTRATIVE
    if _REPORTED_CLAIM_PATTERN.search(segment) is not None:
        return PlanningClaimModality.REPORTED
    return PlanningClaimModality.ASSERTED


def _duration_to_minutes(value: str, unit: str) -> int | None:
    try:
        amount = Decimal(value.replace(",", "."))
    except InvalidOperation:
        return None
    minutes = amount * (60 if unit == "saat" else 1)
    if minutes != minutes.to_integral_value() or minutes < 1:
        return None
    return int(minutes)


def _task_description_contradicts_limit(
    task: StudyTask,
    limit: DailySubjectLimit,
) -> bool:
    if task.area_type == limit.area_type and task.area_code == limit.area_code:
        return False
    pattern = _CONSTRAINED_AREA_DESCRIPTION_PATTERNS.get(
        (limit.area_type, limit.area_code)
    )
    return (
        pattern is not None
        and pattern.search(normalize_response_text(task.description)) is not None
    )


def _to_minutes(value: int, unit: str) -> int:
    return value * 60 if unit == "saat" else value


def _find_matches(
    patterns: tuple[re.Pattern[str], ...],
    text: str,
) -> tuple[re.Match[str], ...]:
    return tuple(
        sorted(
            (
                match
                for pattern in patterns
                for match in pattern.finditer(text)
            ),
            key=lambda match: match.start(),
        )
    )


def _home_arrival_time(match: re.Match[str]) -> time:
    hour = int(match.group("hour"))
    minute_group = match.groupdict().get("minute")
    if minute_group is None:
        return time(hour + 12, 0)
    return time(hour, int(minute_group))
