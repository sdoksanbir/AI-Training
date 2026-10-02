from datetime import date, datetime, timezone

import pytest
from pydantic import ValidationError

from educoach.models import (
    ContextType,
    Learner,
    LearningContext,
    PlanStatus,
    PlanType,
    StudyPlan,
    StudySession,
    StudyTask,
    TaskStatus,
    TaskType,
)


def make_context() -> tuple[Learner, LearningContext]:
    learner = Learner()

    context = LearningContext(
        learner_id=learner.learner_id,
        context_type=ContextType.SCHOOL,
        program_code="school_7",
        grade_level=7,
    )

    return learner, context


def make_plan() -> tuple[Learner, LearningContext, StudyPlan]:
    learner, context = make_context()

    plan = StudyPlan(
        learner_id=learner.learner_id,
        context_id=context.context_id,
        title="Haftalık Çalışma Planı",
        plan_type=PlanType.WEEKLY,
        start_date=date(2026, 10, 5),
        end_date=date(2026, 10, 11),
        status=PlanStatus.ACTIVE,
    )

    return learner, context, plan


def test_plan_date_range_must_be_valid() -> None:
    learner, context = make_context()

    with pytest.raises(ValidationError):
        StudyPlan(
            learner_id=learner.learner_id,
            context_id=context.context_id,
            title="Geçersiz Plan",
            plan_type=PlanType.WEEKLY,
            start_date=date(2026, 10, 10),
            end_date=date(2026, 10, 1),
        )


def test_task_stores_planned_minutes() -> None:
    _, context, plan = make_plan()

    task = StudyTask(
        plan_id=plan.plan_id,
        context_id=context.context_id,
        task_date=date(2026, 10, 5),
        area_type="subject",
        area_code="mathematics",
        task_type=TaskType.PRACTICE,
        description="Matematik soru çalışması",
        planned_minutes=60,
    )

    assert task.planned_minutes == 60
    assert not hasattr(task, "actual_minutes")


def test_task_rejects_zero_planned_minutes() -> None:
    _, context, plan = make_plan()

    with pytest.raises(ValidationError):
        StudyTask(
            plan_id=plan.plan_id,
            context_id=context.context_id,
            task_date=date(2026, 10, 5),
            task_type=TaskType.STUDY,
            description="Çalışma",
            planned_minutes=0,
        )


def test_task_area_fields_must_be_given_together() -> None:
    _, context, plan = make_plan()

    with pytest.raises(ValidationError):
        StudyTask(
            plan_id=plan.plan_id,
            context_id=context.context_id,
            task_date=date(2026, 10, 5),
            area_type="subject",
            task_type=TaskType.STUDY,
            description="Çalışma",
            planned_minutes=45,
        )


def test_completed_task_requires_completed_at() -> None:
    _, context, plan = make_plan()

    with pytest.raises(ValidationError):
        StudyTask(
            plan_id=plan.plan_id,
            context_id=context.context_id,
            task_date=date(2026, 10, 5),
            task_type=TaskType.STUDY,
            description="Tamamlanan görev",
            planned_minutes=45,
            status=TaskStatus.COMPLETED,
        )


def test_non_completed_task_rejects_completed_at() -> None:
    _, context, plan = make_plan()

    with pytest.raises(ValidationError):
        StudyTask(
            plan_id=plan.plan_id,
            context_id=context.context_id,
            task_date=date(2026, 10, 5),
            task_type=TaskType.STUDY,
            description="Bekleyen görev",
            planned_minutes=45,
            status=TaskStatus.PENDING,
            completed_at=datetime(2026, 10, 5, 18, 0, tzinfo=timezone.utc),
        )


def test_session_stores_actual_duration_separately_from_task() -> None:
    learner, context, plan = make_plan()

    task = StudyTask(
        plan_id=plan.plan_id,
        context_id=context.context_id,
        task_date=date(2026, 10, 5),
        task_type=TaskType.PRACTICE,
        description="Matematik çalışması",
        planned_minutes=60,
    )

    session = StudySession(
        learner_id=learner.learner_id,
        context_id=context.context_id,
        task_id=task.task_id,
        duration_minutes=35,
    )

    assert task.planned_minutes == 60
    assert session.duration_minutes == 35


def test_session_rejects_zero_duration() -> None:
    learner, context, _ = make_plan()

    with pytest.raises(ValidationError):
        StudySession(
            learner_id=learner.learner_id,
            context_id=context.context_id,
            duration_minutes=0,
        )


def test_session_timestamps_must_be_given_together() -> None:
    learner, context, _ = make_plan()

    with pytest.raises(ValidationError):
        StudySession(
            learner_id=learner.learner_id,
            context_id=context.context_id,
            started_at=datetime(2026, 10, 5, 18, 0, tzinfo=timezone.utc),
            duration_minutes=30,
        )


def test_session_end_must_be_after_start() -> None:
    learner, context, _ = make_plan()

    with pytest.raises(ValidationError):
        StudySession(
            learner_id=learner.learner_id,
            context_id=context.context_id,
            started_at=datetime(2026, 10, 5, 19, 0, tzinfo=timezone.utc),
            ended_at=datetime(2026, 10, 5, 18, 0, tzinfo=timezone.utc),
            duration_minutes=60,
        )


def test_completion_level_must_be_between_zero_and_one() -> None:
    learner, context, _ = make_plan()

    with pytest.raises(ValidationError):
        StudySession(
            learner_id=learner.learner_id,
            context_id=context.context_id,
            duration_minutes=30,
            completion_level=1.5,
        )
