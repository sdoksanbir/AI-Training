"""Pure availability selection and daily time-budget resolution."""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, time
from enum import StrEnum

from educoach.models import Availability, AvailabilityType


class TimeBudgetResolutionStatus(StrEnum):
    RESOLVED = "resolved"
    UNKNOWN = "unknown"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True)
class DailyTimeBudgetResolution:
    target_date: date
    status: TimeBudgetResolutionStatus
    available_minutes: int | None

    def __post_init__(self) -> None:
        if not isinstance(self.status, TimeBudgetResolutionStatus):
            raise ValueError("status must be a TimeBudgetResolutionStatus")

        if self.status == TimeBudgetResolutionStatus.RESOLVED:
            if (
                isinstance(self.available_minutes, bool)
                or not isinstance(self.available_minutes, int)
                or self.available_minutes < 0
            ):
                raise ValueError(
                    "resolved time budget requires non-negative integer minutes"
                )
        elif self.available_minutes is not None:
            raise ValueError(
                "unknown or ambiguous time budget cannot contain minutes"
            )


def select_applicable_availability(
    availability: Iterable[Availability],
    target_date: date,
) -> tuple[Availability, ...]:
    """Select records matching the weekday and inclusive effective range."""

    return tuple(
        record
        for record in availability
        if int(record.day_of_week) == target_date.weekday()
        and (
            record.effective_from is None
            or record.effective_from <= target_date
        )
        and (
            record.effective_until is None
            or target_date <= record.effective_until
        )
    )


def resolve_daily_time_budget(
    availability: Iterable[Availability],
    target_date: date,
) -> DailyTimeBudgetResolution:
    """Resolve a trustworthy learner-level budget for one explicit date."""

    applicable = select_applicable_availability(availability, target_date)
    available = tuple(
        record
        for record in applicable
        if record.availability_type == AvailabilityType.AVAILABLE
    )

    if not available:
        return DailyTimeBudgetResolution(
            target_date=target_date,
            status=TimeBudgetResolutionStatus.UNKNOWN,
            available_minutes=None,
        )

    minutes_only = tuple(
        record for record in available if record.start_time is None
    )
    timed_available = tuple(
        record for record in available if record.start_time is not None
    )
    blockers = tuple(
        record
        for record in applicable
        if record.availability_type != AvailabilityType.AVAILABLE
    )
    untimed_blockers = tuple(
        record for record in blockers if record.start_time is None
    )
    timed_blockers = tuple(
        record for record in blockers if record.start_time is not None
    )

    if minutes_only:
        if (
            len(minutes_only) == 1
            and not timed_available
            and not blockers
        ):
            return DailyTimeBudgetResolution(
                target_date=target_date,
                status=TimeBudgetResolutionStatus.RESOLVED,
                available_minutes=minutes_only[0].available_minutes,
            )

        return DailyTimeBudgetResolution(
            target_date=target_date,
            status=TimeBudgetResolutionStatus.AMBIGUOUS,
            available_minutes=None,
        )

    if untimed_blockers:
        return DailyTimeBudgetResolution(
            target_date=target_date,
            status=TimeBudgetResolutionStatus.AMBIGUOUS,
            available_minutes=None,
        )

    available_intervals = _merge_intervals(
        _record_interval(record) for record in timed_available
    )
    blocker_intervals = _merge_intervals(
        _record_interval(record) for record in timed_blockers
    )
    available_minutes = _interval_duration(available_intervals)
    blocked_minutes = sum(
        max(0, min(available_end, blocker_end) - max(available_start, blocker_start))
        for available_start, available_end in available_intervals
        for blocker_start, blocker_end in blocker_intervals
    )

    return DailyTimeBudgetResolution(
        target_date=target_date,
        status=TimeBudgetResolutionStatus.RESOLVED,
        available_minutes=max(0, available_minutes - blocked_minutes),
    )


def _record_interval(record: Availability) -> tuple[int, int]:
    assert record.start_time is not None
    assert record.end_time is not None
    return _minute_of_day(record.start_time), _minute_of_day(record.end_time)


def _minute_of_day(value: time) -> int:
    return value.hour * 60 + value.minute


def _merge_intervals(
    intervals: Iterable[tuple[int, int]],
) -> tuple[tuple[int, int], ...]:
    merged: list[tuple[int, int]] = []

    for start, end in sorted(intervals):
        if not merged or start > merged[-1][1]:
            merged.append((start, end))
            continue

        previous_start, previous_end = merged[-1]
        merged[-1] = (previous_start, max(previous_end, end))

    return tuple(merged)


def _interval_duration(intervals: Iterable[tuple[int, int]]) -> int:
    return sum(end - start for start, end in intervals)
