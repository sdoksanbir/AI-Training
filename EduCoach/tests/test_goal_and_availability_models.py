from datetime import date, time

import pytest
from pydantic import ValidationError

from educoach.models import (
    Availability,
    AvailabilityType,
    ContextType,
    DayOfWeek,
    Goal,
    GoalPriority,
    GoalStatus,
    Learner,
    LearningContext,
)


def test_goal_can_be_attached_to_a_learning_context() -> None:
    learner = Learner()

    context = LearningContext(
        learner_id=learner.learner_id,
        context_type=ContextType.LANGUAGE_EXAM,
        program_code="yds",
    )

    goal = Goal(
        learner_id=learner.learner_id,
        context_id=context.context_id,
        goal_type="score_target",
        description="YDS hedef puanı",
        target_value=70,
        target_unit="score",
        priority=GoalPriority.HIGH,
    )

    assert goal.context_id == context.context_id
    assert goal.target_value == 70
    assert goal.status == GoalStatus.ACTIVE


def test_goal_does_not_require_a_numeric_target() -> None:
    learner = Learner()

    goal = Goal(
        learner_id=learner.learner_id,
        goal_type="study_habit",
        description="Düzenli çalışma alışkanlığı oluşturmak",
    )

    assert goal.target_value is None
    assert goal.target_unit is None


def test_available_minutes_cannot_be_negative() -> None:
    learner = Learner()

    with pytest.raises(ValidationError):
        Availability(
            learner_id=learner.learner_id,
            day_of_week=DayOfWeek.MONDAY,
            availability_type=AvailabilityType.AVAILABLE,
            available_minutes=-1,
        )


def test_available_entry_requires_minutes_or_time_range() -> None:
    learner = Learner()

    with pytest.raises(ValidationError):
        Availability(
            learner_id=learner.learner_id,
            day_of_week=DayOfWeek.MONDAY,
            availability_type=AvailabilityType.AVAILABLE,
        )


def test_valid_time_range_is_accepted() -> None:
    learner = Learner()

    availability = Availability(
        learner_id=learner.learner_id,
        day_of_week=DayOfWeek.TUESDAY,
        availability_type=AvailabilityType.AVAILABLE,
        start_time=time(18, 0),
        end_time=time(20, 0),
    )

    assert availability.start_time == time(18, 0)
    assert availability.end_time == time(20, 0)


def test_invalid_time_range_is_rejected() -> None:
    learner = Learner()

    with pytest.raises(ValidationError):
        Availability(
            learner_id=learner.learner_id,
            day_of_week=DayOfWeek.TUESDAY,
            availability_type=AvailabilityType.FIXED_COMMITMENT,
            start_time=time(20, 0),
            end_time=time(18, 0),
        )


def test_effective_date_range_must_be_valid() -> None:
    learner = Learner()

    with pytest.raises(ValidationError):
        Availability(
            learner_id=learner.learner_id,
            day_of_week=DayOfWeek.WEDNESDAY,
            availability_type=AvailabilityType.AVAILABLE,
            available_minutes=120,
            effective_from=date(2026, 10, 10),
            effective_until=date(2026, 10, 1),
        )


def test_availability_rejects_unknown_evidence_source() -> None:
    learner = Learner()

    with pytest.raises(ValidationError):
        Availability(
            learner_id=learner.learner_id,
            day_of_week=DayOfWeek.FRIDAY,
            availability_type=AvailabilityType.AVAILABLE,
            available_minutes=120,
            source_type="uydurma_kaynak",
        )
