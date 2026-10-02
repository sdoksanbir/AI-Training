from datetime import date, datetime, time, timezone

import pytest
from pydantic import ValidationError

from educoach.models import (
    Availability,
    AvailabilityType,
    ContextType,
    DayOfWeek,
    EvidenceSource,
    Goal,
    Learner,
    LearningContext,
    PlanType,
    StudyPlan,
    StudySession,
)


def make_context() -> tuple[Learner, LearningContext]:
    learner = Learner()

    context = LearningContext(
        learner_id=learner.learner_id,
        context_type=ContextType.SCHOOL,
        program_code="school_11",
        grade_level=11,
    )

    return learner, context


def test_parent_reported_is_supported_as_evidence_source() -> None:
    assert EvidenceSource.PARENT_REPORTED == "parent_reported"


def test_study_plan_can_span_multiple_contexts() -> None:
    learner = Learner()

    plan = StudyPlan(
        learner_id=learner.learner_id,
        title="Karma günlük çalışma planı",
        plan_type=PlanType.DAILY,
        start_date=date(2026, 10, 3),
        end_date=date(2026, 10, 3),
    )

    assert plan.context_id is None


def test_goal_target_value_requires_unit() -> None:
    learner, context = make_context()

    with pytest.raises(ValidationError):
        Goal(
            learner_id=learner.learner_id,
            context_id=context.context_id,
            goal_type="exam_target",
            description="Deneme sonucunu yükselt",
            target_value=70,
        )


def test_goal_target_unit_requires_value() -> None:
    learner, context = make_context()

    with pytest.raises(ValidationError):
        Goal(
            learner_id=learner.learner_id,
            context_id=context.context_id,
            goal_type="exam_target",
            description="Deneme sonucunu yükselt",
            target_unit="net",
        )


def test_availability_minutes_must_match_time_range() -> None:
    learner = Learner()

    with pytest.raises(ValidationError):
        Availability(
            learner_id=learner.learner_id,
            day_of_week=DayOfWeek.MONDAY,
            availability_type=AvailabilityType.AVAILABLE,
            start_time=time(18, 0),
            end_time=time(20, 0),
            available_minutes=60,
        )


def test_available_minutes_cannot_be_used_for_unavailable_record() -> None:
    learner = Learner()

    with pytest.raises(ValidationError):
        Availability(
            learner_id=learner.learner_id,
            day_of_week=DayOfWeek.TUESDAY,
            availability_type=AvailabilityType.UNAVAILABLE,
            available_minutes=90,
        )


def test_session_duration_must_match_timestamps() -> None:
    learner, context = make_context()

    with pytest.raises(ValidationError):
        StudySession(
            learner_id=learner.learner_id,
            context_id=context.context_id,
            started_at=datetime(
                2026, 10, 3, 18, 0, tzinfo=timezone.utc
            ),
            ended_at=datetime(
                2026, 10, 3, 19, 0, tzinfo=timezone.utc
            ),
            duration_minutes=30,
        )


def test_session_accepts_matching_duration_and_timestamps() -> None:
    learner, context = make_context()

    session = StudySession(
        learner_id=learner.learner_id,
        context_id=context.context_id,
        started_at=datetime(
            2026, 10, 3, 18, 0, tzinfo=timezone.utc
        ),
        ended_at=datetime(
            2026, 10, 3, 19, 0, tzinfo=timezone.utc
        ),
        duration_minutes=60,
    )

    assert session.duration_minutes == 60
