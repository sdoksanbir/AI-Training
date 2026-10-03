from dataclasses import FrozenInstanceError
from datetime import date, time
from typing import cast
from uuid import uuid4

import pytest

from educoach.models import Availability, AvailabilityType, DayOfWeek
from educoach.rules import (
    DailyTimeBudgetResolution,
    TimeBudgetResolutionStatus,
    resolve_daily_time_budget,
    select_applicable_availability,
)


TARGET_DATE = date(2026, 10, 5)
LEARNER_ID = uuid4()


def make_available(
    *,
    minutes: int | None = None,
    start: time | None = None,
    end: time | None = None,
    day: DayOfWeek = DayOfWeek.MONDAY,
    effective_from: date | None = None,
    effective_until: date | None = None,
) -> Availability:
    return Availability(
        learner_id=LEARNER_ID,
        day_of_week=day,
        availability_type=AvailabilityType.AVAILABLE,
        available_minutes=minutes,
        start_time=start,
        end_time=end,
        effective_from=effective_from,
        effective_until=effective_until,
    )


def make_blocker(
    blocker_type: AvailabilityType,
    *,
    start: time | None = None,
    end: time | None = None,
) -> Availability:
    return Availability(
        learner_id=LEARNER_ID,
        day_of_week=DayOfWeek.MONDAY,
        availability_type=blocker_type,
        start_time=start,
        end_time=end,
    )


def assert_resolution(
    records: tuple[Availability, ...],
    status: TimeBudgetResolutionStatus,
    minutes: int | None,
) -> None:
    result = resolve_daily_time_budget(records, TARGET_DATE)
    assert result.status is status
    assert result.available_minutes == minutes
    assert result.target_date == TARGET_DATE


def test_selector_includes_matching_weekday() -> None:
    record = make_available(minutes=60)
    assert select_applicable_availability((record,), TARGET_DATE) == (record,)


def test_selector_excludes_wrong_weekday() -> None:
    record = make_available(minutes=60, day=DayOfWeek.TUESDAY)
    assert select_applicable_availability((record,), TARGET_DATE) == ()


def test_selector_includes_effective_from_boundary() -> None:
    record = make_available(minutes=60, effective_from=TARGET_DATE)
    assert select_applicable_availability((record,), TARGET_DATE) == (record,)


def test_selector_includes_effective_until_boundary() -> None:
    record = make_available(minutes=60, effective_until=TARGET_DATE)
    assert select_applicable_availability((record,), TARGET_DATE) == (record,)


def test_selector_excludes_date_before_effective_from() -> None:
    record = make_available(minutes=60, effective_from=date(2026, 10, 6))
    assert select_applicable_availability((record,), TARGET_DATE) == ()


def test_selector_excludes_date_after_effective_until() -> None:
    record = make_available(minutes=60, effective_until=date(2026, 10, 4))
    assert select_applicable_availability((record,), TARGET_DATE) == ()


def test_selector_preserves_input_order() -> None:
    first = make_available(minutes=30)
    excluded = make_available(minutes=45, day=DayOfWeek.TUESDAY)
    second = make_available(start=time(18), end=time(19))

    assert select_applicable_availability(
        (first, excluded, second), TARGET_DATE
    ) == (first, second)


def test_minutes_only_available_resolves() -> None:
    assert_resolution(
        (make_available(minutes=90),),
        TimeBudgetResolutionStatus.RESOLVED,
        90,
    )


def test_explicit_zero_minutes_resolves_to_zero() -> None:
    assert_resolution(
        (make_available(minutes=0),),
        TimeBudgetResolutionStatus.RESOLVED,
        0,
    )


def test_single_timed_available_resolves() -> None:
    assert_resolution(
        (make_available(start=time(18), end=time(20)),),
        TimeBudgetResolutionStatus.RESOLVED,
        120,
    )


def test_timed_available_with_matching_minutes_is_counted_once() -> None:
    assert_resolution(
        (make_available(minutes=120, start=time(18), end=time(20)),),
        TimeBudgetResolutionStatus.RESOLVED,
        120,
    )


def test_non_overlapping_timed_available_intervals_are_summed() -> None:
    records = (
        make_available(start=time(18), end=time(19)),
        make_available(start=time(20), end=time(21)),
    )
    assert_resolution(records, TimeBudgetResolutionStatus.RESOLVED, 120)


def test_overlapping_timed_available_intervals_are_merged() -> None:
    records = (
        make_available(start=time(18), end=time(20)),
        make_available(start=time(19), end=time(21)),
    )
    assert_resolution(records, TimeBudgetResolutionStatus.RESOLVED, 180)


def test_nested_timed_available_intervals_are_merged() -> None:
    records = (
        make_available(start=time(18), end=time(21)),
        make_available(start=time(19), end=time(20)),
    )
    assert_resolution(records, TimeBudgetResolutionStatus.RESOLVED, 180)


def test_duplicate_timed_available_intervals_are_counted_once() -> None:
    records = (
        make_available(start=time(18), end=time(20)),
        make_available(start=time(18), end=time(20)),
    )
    assert_resolution(records, TimeBudgetResolutionStatus.RESOLVED, 120)


def test_timed_unavailable_is_subtracted_from_available_union() -> None:
    records = (
        make_available(start=time(18), end=time(21)),
        make_blocker(
            AvailabilityType.UNAVAILABLE,
            start=time(19),
            end=time(20),
        ),
    )
    assert_resolution(records, TimeBudgetResolutionStatus.RESOLVED, 120)


def test_timed_fixed_commitment_is_subtracted_from_available_union() -> None:
    records = (
        make_available(start=time(18), end=time(21)),
        make_blocker(
            AvailabilityType.FIXED_COMMITMENT,
            start=time(19),
            end=time(20),
        ),
    )
    assert_resolution(records, TimeBudgetResolutionStatus.RESOLVED, 120)


def test_overlapping_blockers_are_subtracted_only_once() -> None:
    records = (
        make_available(start=time(18), end=time(22)),
        make_blocker(
            AvailabilityType.UNAVAILABLE,
            start=time(19),
            end=time(21),
        ),
        make_blocker(
            AvailabilityType.FIXED_COMMITMENT,
            start=time(20),
            end=time(22),
        ),
    )
    assert_resolution(records, TimeBudgetResolutionStatus.RESOLVED, 60)


def test_blocker_outside_available_union_has_no_effect() -> None:
    records = (
        make_available(start=time(18), end=time(20)),
        make_blocker(
            AvailabilityType.UNAVAILABLE,
            start=time(20),
            end=time(21),
        ),
    )
    assert_resolution(records, TimeBudgetResolutionStatus.RESOLVED, 120)


def test_full_blocker_resolves_to_zero_without_going_negative() -> None:
    records = (
        make_available(start=time(18), end=time(20)),
        make_blocker(
            AvailabilityType.UNAVAILABLE,
            start=time(17),
            end=time(21),
        ),
    )
    assert_resolution(records, TimeBudgetResolutionStatus.RESOLVED, 0)


def test_multiple_minutes_only_available_records_are_ambiguous() -> None:
    records = (make_available(minutes=60), make_available(minutes=90))
    assert_resolution(records, TimeBudgetResolutionStatus.AMBIGUOUS, None)


def test_minutes_only_and_timed_available_are_ambiguous() -> None:
    records = (
        make_available(minutes=60),
        make_available(start=time(18), end=time(19)),
    )
    assert_resolution(records, TimeBudgetResolutionStatus.AMBIGUOUS, None)


@pytest.mark.parametrize(
    "blocker_type",
    [AvailabilityType.UNAVAILABLE, AvailabilityType.FIXED_COMMITMENT],
)
def test_minutes_only_available_with_timed_blocker_is_ambiguous(
    blocker_type: AvailabilityType,
) -> None:
    records = (
        make_available(minutes=60),
        make_blocker(blocker_type, start=time(18), end=time(19)),
    )
    assert_resolution(records, TimeBudgetResolutionStatus.AMBIGUOUS, None)


@pytest.mark.parametrize(
    "blocker_type",
    [AvailabilityType.UNAVAILABLE, AvailabilityType.FIXED_COMMITMENT],
)
def test_timed_available_with_untimed_blocker_is_ambiguous(
    blocker_type: AvailabilityType,
) -> None:
    records = (
        make_available(start=time(18), end=time(20)),
        make_blocker(blocker_type),
    )
    assert_resolution(records, TimeBudgetResolutionStatus.AMBIGUOUS, None)


def test_no_applicable_records_is_unknown() -> None:
    assert_resolution((), TimeBudgetResolutionStatus.UNKNOWN, None)


@pytest.mark.parametrize(
    "blocker_type",
    [AvailabilityType.UNAVAILABLE, AvailabilityType.FIXED_COMMITMENT],
)
def test_only_timed_blocker_is_unknown(
    blocker_type: AvailabilityType,
) -> None:
    records = (make_blocker(blocker_type, start=time(18), end=time(19)),)
    assert_resolution(records, TimeBudgetResolutionStatus.UNKNOWN, None)


@pytest.mark.parametrize(
    "blocker_type",
    [AvailabilityType.UNAVAILABLE, AvailabilityType.FIXED_COMMITMENT],
)
def test_only_untimed_blocker_is_unknown(
    blocker_type: AvailabilityType,
) -> None:
    assert_resolution(
        (make_blocker(blocker_type),),
        TimeBudgetResolutionStatus.UNKNOWN,
        None,
    )


def test_time_budget_status_has_three_controlled_values() -> None:
    assert list(TimeBudgetResolutionStatus) == [
        TimeBudgetResolutionStatus.RESOLVED,
        TimeBudgetResolutionStatus.UNKNOWN,
        TimeBudgetResolutionStatus.AMBIGUOUS,
    ]
    assert [status.value for status in TimeBudgetResolutionStatus] == [
        "resolved",
        "unknown",
        "ambiguous",
    ]


@pytest.mark.parametrize("raw_status", ["invalid", "resolved"])
def test_time_budget_resolution_rejects_raw_string_status(
    raw_status: str,
) -> None:
    with pytest.raises(ValueError):
        DailyTimeBudgetResolution(
            target_date=TARGET_DATE,
            status=cast(TimeBudgetResolutionStatus, raw_status),
            available_minutes=None,
        )


def test_time_budget_resolution_is_frozen() -> None:
    result = DailyTimeBudgetResolution(
        target_date=TARGET_DATE,
        status=TimeBudgetResolutionStatus.RESOLVED,
        available_minutes=60,
    )

    with pytest.raises(FrozenInstanceError):
        result.available_minutes = 90


@pytest.mark.parametrize("minutes", [None, -1, 1.5, True])
def test_resolved_budget_requires_non_negative_integer(minutes) -> None:
    with pytest.raises(ValueError):
        DailyTimeBudgetResolution(
            target_date=TARGET_DATE,
            status=TimeBudgetResolutionStatus.RESOLVED,
            available_minutes=minutes,
        )


@pytest.mark.parametrize(
    "status",
    [TimeBudgetResolutionStatus.UNKNOWN, TimeBudgetResolutionStatus.AMBIGUOUS],
)
def test_unresolved_budget_rejects_numeric_value(
    status: TimeBudgetResolutionStatus,
) -> None:
    with pytest.raises(ValueError):
        DailyTimeBudgetResolution(
            target_date=TARGET_DATE,
            status=status,
            available_minutes=0,
        )
