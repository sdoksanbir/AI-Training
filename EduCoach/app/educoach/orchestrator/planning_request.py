"""Typed, request-local planning constraints from explicit user language."""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, time
from enum import StrEnum
import re

from educoach.rules import RuleSeverity, RuleViolation
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


_SUBJECT_LIMIT = re.compile(
    r"\bmatematige\s+gunde\s+en\s+fazla\s+"
    r"(?P<value>\d{1,3})\s*(?P<unit>saat|dakika)\s+ayirabilirim\b"
)
_SESSION_TOLERANCE = re.compile(
    r"\b(?P<value>\d{1,3})\s*(?P<unit>saat|dakika)\s+"
    r"sonra\s+sikiliyorum\b"
)
_RECURRING_COMMITMENT = re.compile(
    r"\bhaftada\s+(?P<count>\d{1,2}|uc)\s+hafta\s+ici\s+gunu\s+"
    r"ingilizce\s+kursum\s+var\b"
)
_HOME_ARRIVAL = re.compile(
    r"\beve\s+(?P<hour>[01]?\d|2[0-3]):(?P<minute>[0-5]\d)"
    r"(?:['’]?de)?\s+geliyorum\b"
)
_DAILY_WORKLOAD = re.compile(
    r"\b(?:her\s+gun|gunde)\s+(?:yaklasik\s+)?"
    r"(?P<minimum>\d{1,3})(?:\s*[-–—]\s*(?P<maximum>\d{1,3}))?\s*"
    r"(?P<unit>saat|dakika)\s+calis(?:\.|!|$)"
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
        for match in _SUBJECT_LIMIT.finditer(normalized)
    )
    tolerances = tuple(
        SessionTolerance(
            preferred_max_continuous_minutes=_to_minutes(
                int(match.group("value")), match.group("unit")
            )
        )
        for match in _SESSION_TOLERANCE.finditer(normalized)
    )
    commitments = tuple(
        RecurringCommitmentSummary(
            subject="english_course",
            occurrence_count=(
                3 if match.group("count") == "uc" else int(match.group("count"))
            ),
            day_scope=RecurringDayScope.WEEKDAY,
        )
        for match in _RECURRING_COMMITMENT.finditer(normalized)
    )
    anchors = tuple(
        ScheduleAnchor(
            anchor_type=ScheduleAnchorType.HOME_ARRIVAL,
            anchor_time=time(
                int(match.group("hour")), int(match.group("minute"))
            ),
        )
        for match in _HOME_ARRIVAL.finditer(normalized)
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
    matches = tuple(_DAILY_WORKLOAD.finditer(normalized))
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


def _to_minutes(value: int, unit: str) -> int:
    return value * 60 if unit == "saat" else value
