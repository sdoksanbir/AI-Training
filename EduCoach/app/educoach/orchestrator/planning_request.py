"""Typed, request-local planning constraints from explicit user language."""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, time
from enum import StrEnum
import re

from educoach.models import AvailabilityType, TaskType
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
_DAILY_WORKLOAD_PATTERNS = (
    re.compile(
        r"\b(?:her\s+gun|gunde)\s+(?:yaklasik\s+)?"
        r"(?P<minimum>\d{1,3})"
        r"(?:\s*[-–—]\s*(?P<maximum>\d{1,3}))?\s*"
        r"(?P<unit>saat|dakika)\s+calis(?:\.|!|$)"
    ),
    re.compile(
        r"\b(?:her\s+gun|gunde)\s+"
        r"(?P<minimum>\d{1,3})"
        r"(?:\s*[-–—]\s*(?P<maximum>\d{1,3}))?\s*"
        r"(?P<unit>saat|dakika)lik\s+toplam\s+calisma\s+suresi\s+"
        r"(?:planlanmistir|onerilmistir|planliyorum|oneriyorum)\b"
    ),
    re.compile(
        r"\b(?:her\s+gun|gunde)\s+"
        r"(?P<minimum>\d{1,3})"
        r"(?:\s*[-–—]\s*(?P<maximum>\d{1,3}))?\s*"
        r"(?P<unit>saat|dakika)lik\s+bir\s+calisma\s+plani\s+"
        r"(?:planliyorum|oneriyorum)\b"
    ),
    re.compile(
        r"\b(?:her\s+gun|gunde)\s+"
        r"(?P<minimum>\d{1,3})"
        r"(?:\s*[-–—]\s*(?P<maximum>\d{1,3}))?\s*"
        r"(?P<unit>saat|dakika)\s+calisarak\s+ilerleyebilirsin\b"
    ),
    re.compile(
        r"\b(?:her\s+gun|gunde|gunluk)\s+(?:toplam\s+)?"
        r"(?P<minimum>\d{1,3})"
        r"(?:\s*[-–—]\s*(?P<maximum>\d{1,3}))?\s*"
        r"(?P<unit>saat|dakika)\s+"
        r"(?:calismalisin|calismalisiniz|calisman\s+gerekir|"
        r"calismaniz\s+gerekir)\b"
    ),
    re.compile(
        r"\bgunluk\s+program\s*\(\s*"
        r"(?P<minimum>\d{1,3})"
        r"(?:\s*[-–—]\s*(?P<maximum>\d{1,3}))?\s*"
        r"(?P<unit>saat|dakika)\s*\)\s*"
        r"(?:(?:\*\*|__)\s*:|:\s*(?:\*\*|__)|(?:\*\*|__)|:)?"
        r"(?=\s*(?:$|[\r\n]))"
    ),
    re.compile(
        r"\bgunluk\s+calisma(?:\s+suresi)?\s*:\s*"
        r"(?P<minimum>\d{1,3})"
        r"(?:\s*[-–—]\s*(?P<maximum>\d{1,3}))?\s*"
        r"(?P<unit>saat|dakika)\b"
    ),
)
_TOTAL_WORKLOAD_PATTERN = re.compile(
    r"\btoplam\s+(?P<minimum>\d{1,3})"
    r"(?:\s*[-–—]\s*(?P<maximum>\d{1,3}))?\s*"
    r"(?P<unit>saat|dakika)\s+"
    r"(?:calismalisin|calismalisiniz|calisman\s+gerekir|"
    r"calismaniz\s+gerekir)\b"
)
_CLOCK_RANGE_PATTERN = re.compile(
    r"(?<!\d)(?:[01]?\d|2[0-3])[:.]?[0-5]\d\s*[-–—]\s*"
    r"(?:[01]?\d|2[0-3])[:.]?[0-5]\d(?!\d)"
)
_STUDY_ACTIVITY_PATTERN = re.compile(
    r"\b(?:calis|ders|odev|tyt|ayt|matematik|fizik|kimya|biyoloji|"
    r"turkce|sosyal|ingilizce|konu|soru|test|tekrar|pratik|okuma)\w*\b"
)
_STUDY_ACTION_PATTERN = re.compile(
    r"\b(?:calis|coz|yap|tamamla|tekrar\s+et|oku|incele)\w*\b"
)
_NON_ASSIGNING_SCHEDULE_PATTERN = re.compile(
    r"\b(?:eger|ornegin|mesela|musait|uygunsa|vaktin\s+varsa|"
    r"vaktiniz\s+varsa|bilmiyorum|bilmeden|netlestir|belirleyemem)\w*\b"
)
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
        and (task.area_type is None or task.area_code is None)
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
    """Parse one explicit, unconditional numeric daily workload statement."""

    normalized = normalize_response_text(text)
    matches = _find_matches(_DAILY_WORKLOAD_PATTERNS, normalized)
    if not matches and _has_high_confidence_daily_schedule_context(normalized):
        total_match = _TOTAL_WORKLOAD_PATTERN.search(normalized)
        matches = (total_match,) if total_match is not None else ()
    if len(matches) != 1:
        return None
    match = matches[0]
    minimum = int(match.group("minimum"))
    maximum = int(match.group("maximum") or minimum)
    unit = match.group("unit")
    return DailyWorkloadClaim(
        min_minutes_per_day=_to_minutes(minimum, unit),
        max_minutes_per_day=_to_minutes(maximum, unit),
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
    unsupported_clock_schedule = (
        has_unresolved_home_arrival
        and _has_unconditional_study_clock_assignment(response_text)
    )
    unsupported_daily_workload = (
        proposal is None
        and extract_daily_workload_claim(response_text) is not None
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

    claim = extract_daily_workload_claim(response_text)
    if claim is None:
        return ()

    totals: defaultdict[date, int] = defaultdict(int)
    for task in proposal.tasks:
        totals[task.task_date] += task.planned_minutes
    if not totals or all(
        claim.min_minutes_per_day <= total <= claim.max_minutes_per_day
        for total in totals.values()
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


def _has_unconditional_study_clock_assignment(text: str) -> bool:
    normalized = normalize_response_text(text)
    segments = tuple(
        segment
        for segment in re.split(r"(?<=[.!?])\s+|[\r\n]+", normalized)
        if re.search(r"\w", segment)
    )
    for index, segment in enumerate(segments):
        clock_range = _CLOCK_RANGE_PATTERN.search(segment)
        if clock_range is None:
            continue
        if _NON_ASSIGNING_SCHEDULE_PATTERN.search(segment) is not None:
            continue
        tail = segment[clock_range.end():]
        has_schedule_separator = tail.lstrip().startswith(":")
        has_same_line_activity = (
            _STUDY_ACTIVITY_PATTERN.search(segment) is not None
        )
        if has_same_line_activity and (
            has_schedule_separator or _STUDY_ACTION_PATTERN.search(segment)
        ):
            return True
        if not _is_clock_only_segment(segment, clock_range):
            continue
        if index + 1 >= len(segments):
            continue
        assignment = segments[index + 1]
        if _NON_ASSIGNING_SCHEDULE_PATTERN.search(assignment) is not None:
            continue
        if (
            _STUDY_ACTIVITY_PATTERN.search(assignment) is not None
            and _STUDY_ACTION_PATTERN.search(assignment) is not None
        ):
            return True
    return False


def _is_clock_only_segment(segment: str, clock_range: re.Match[str]) -> bool:
    remainder = segment[:clock_range.start()] + segment[clock_range.end():]
    return re.fullmatch(r"[\s:*_`#>\-]*", remainder) is not None


def _has_high_confidence_daily_schedule_context(normalized: str) -> bool:
    if re.search(r"\b(?:gunluk|her\s+gun|gunde)\b", normalized):
        return True
    return len(_CLOCK_RANGE_PATTERN.findall(normalized)) >= 2


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
