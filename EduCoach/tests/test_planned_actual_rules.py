from dataclasses import FrozenInstanceError
from datetime import date, datetime, timezone
from uuid import UUID, uuid4

import pytest

from educoach.models import (
    Learner,
    StudySession,
    StudyTask,
    TaskStatus,
    TaskType,
)
from educoach.rules import (
    PlannedActualFacts,
    TaskStudyActualFact,
    project_planned_actual_facts,
)
from educoach.services.snapshot import LearnerMemorySnapshot


def make_task(
    *,
    task_id: UUID | None = None,
    context_id: UUID | None = None,
    planned_minutes: int = 60,
    status: TaskStatus = TaskStatus.PENDING,
) -> StudyTask:
    values = {
        "plan_id": uuid4(),
        "context_id": context_id or uuid4(),
        "task_date": date(2026, 10, 5),
        "task_type": TaskType.STUDY,
        "description": "Task",
        "planned_minutes": planned_minutes,
        "status": status,
        "completed_at": (
            datetime(2026, 10, 5, 12, tzinfo=timezone.utc)
            if status == TaskStatus.COMPLETED
            else None
        ),
    }
    if task_id is not None:
        values["task_id"] = task_id
    return StudyTask(**values)


def make_session(
    learner: Learner,
    *,
    task: StudyTask | None = None,
    session_id: UUID | None = None,
    context_id: UUID | None = None,
    duration_minutes: int = 20,
    completion_level: float | None = None,
) -> StudySession:
    values = {
        "learner_id": learner.learner_id,
        "context_id": context_id or (task.context_id if task else uuid4()),
        "task_id": task.task_id if task else None,
        "duration_minutes": duration_minutes,
        "completion_level": completion_level,
    }
    if session_id is not None:
        values["session_id"] = session_id
    return StudySession(**values)


def make_snapshot(
    learner: Learner,
    *,
    tasks: tuple[StudyTask, ...] = (),
    sessions: tuple[StudySession, ...] = (),
) -> LearnerMemorySnapshot:
    return LearnerMemorySnapshot(
        learner=learner,
        contexts=(),
        goals=(),
        availability=(),
        assessments=(),
        assessment_results=(),
        learning_evidence=(),
        study_plans=(),
        study_tasks=tasks,
        study_sessions=sessions,
        preferences=(),
        coaching_states=(),
    )


def test_task_without_sessions_preserves_planned_and_has_zero_actual() -> None:
    learner = Learner()
    task = make_task(planned_minutes=75)

    facts = project_planned_actual_facts(make_snapshot(learner, tasks=(task,)))

    assert facts.task_facts == (
        TaskStudyActualFact(task.task_id, 75, 0, ()),
    )


def test_multiple_sessions_produce_cumulative_actual_minutes() -> None:
    learner = Learner()
    task = make_task(planned_minutes=60)
    first = make_session(learner, task=task, duration_minutes=20)
    second = make_session(learner, task=task, duration_minutes=35)

    facts = project_planned_actual_facts(
        make_snapshot(learner, tasks=(task,), sessions=(second, first))
    )

    fact = facts.task_facts[0]
    assert fact.planned_minutes == 60
    assert fact.actual_minutes == 55
    assert fact.session_ids == tuple(
        sorted((first.session_id, second.session_id), key=str)
    )


def test_taskless_sessions_are_aggregated_as_unassigned() -> None:
    learner = Learner()
    first = make_session(learner, duration_minutes=15)
    second = make_session(learner, duration_minutes=25)

    facts = project_planned_actual_facts(
        make_snapshot(learner, sessions=(second, first))
    )

    assert facts.task_facts == ()
    assert facts.unassigned_actual_minutes == 40
    assert facts.unassigned_session_ids == tuple(
        sorted((first.session_id, second.session_id), key=str)
    )


def test_completion_level_does_not_change_actual_minutes() -> None:
    learner = Learner()
    task = make_task()
    session = make_session(
        learner,
        task=task,
        duration_minutes=18,
        completion_level=1,
    )

    facts = project_planned_actual_facts(
        make_snapshot(learner, tasks=(task,), sessions=(session,))
    )

    assert facts.task_facts[0].actual_minutes == 18


@pytest.mark.parametrize(
    "status",
    [
        TaskStatus.IN_PROGRESS,
        TaskStatus.COMPLETED,
        TaskStatus.SKIPPED,
        TaskStatus.CANCELLED,
    ],
)
def test_task_status_does_not_erase_recorded_actual(status: TaskStatus) -> None:
    learner = Learner()
    task = make_task(status=status)
    session = make_session(learner, task=task, duration_minutes=12)

    facts = project_planned_actual_facts(
        make_snapshot(learner, tasks=(task,), sessions=(session,))
    )

    assert facts.task_facts[0].actual_minutes == 12


def test_projection_does_not_force_planned_and_actual_to_match() -> None:
    learner = Learner()
    task = make_task(planned_minutes=90)
    session = make_session(learner, task=task, duration_minutes=25)

    fact = project_planned_actual_facts(
        make_snapshot(learner, tasks=(task,), sessions=(session,))
    ).task_facts[0]

    assert (fact.planned_minutes, fact.actual_minutes) == (90, 25)


def test_duplicate_task_id_is_rejected() -> None:
    learner = Learner()
    task_id = uuid4()

    with pytest.raises(ValueError, match="duplicate task_id"):
        project_planned_actual_facts(
            make_snapshot(
                learner,
                tasks=(make_task(task_id=task_id), make_task(task_id=task_id)),
            )
        )


def test_duplicate_session_id_is_rejected() -> None:
    learner = Learner()
    session_id = uuid4()

    with pytest.raises(ValueError, match="duplicate session_id"):
        project_planned_actual_facts(
            make_snapshot(
                learner,
                sessions=(
                    make_session(learner, session_id=session_id),
                    make_session(learner, session_id=session_id),
                ),
            )
        )


def test_session_for_another_learner_is_rejected() -> None:
    learner = Learner()
    session = make_session(Learner())

    with pytest.raises(ValueError, match="snapshot learner"):
        project_planned_actual_facts(
            make_snapshot(learner, sessions=(session,))
        )


def test_linked_session_without_snapshot_task_is_rejected() -> None:
    learner = Learner()
    task = make_task()
    session = make_session(learner, task=task)

    with pytest.raises(ValueError, match="snapshot task"):
        project_planned_actual_facts(
            make_snapshot(learner, sessions=(session,))
        )


def test_linked_session_with_wrong_context_is_rejected() -> None:
    learner = Learner()
    task = make_task()
    session = make_session(learner, task=task, context_id=uuid4())

    with pytest.raises(ValueError, match="task context"):
        project_planned_actual_facts(
            make_snapshot(learner, tasks=(task,), sessions=(session,))
        )


def test_task_and_session_order_is_deterministic() -> None:
    learner = Learner()
    first_task = make_task(task_id=UUID(int=1))
    second_task = make_task(task_id=UUID(int=2))
    first_session = make_session(
        learner,
        task=first_task,
        session_id=UUID(int=3),
    )
    second_session = make_session(
        learner,
        task=first_task,
        session_id=UUID(int=4),
    )

    facts = project_planned_actual_facts(
        make_snapshot(
            learner,
            tasks=(second_task, first_task),
            sessions=(second_session, first_session),
        )
    )

    assert tuple(fact.task_id for fact in facts.task_facts) == (
        first_task.task_id,
        second_task.task_id,
    )
    assert facts.task_facts[0].session_ids == (
        first_session.session_id,
        second_session.session_id,
    )


def test_fact_contracts_are_immutable() -> None:
    fact = TaskStudyActualFact(uuid4(), 30, 0, ())
    facts = PlannedActualFacts((fact,), 0, ())

    with pytest.raises(FrozenInstanceError):
        fact.actual_minutes = 1
    with pytest.raises(FrozenInstanceError):
        facts.unassigned_actual_minutes = 1


@pytest.mark.parametrize("value", [True, -1])
def test_fact_contracts_reject_invalid_minutes(value: int) -> None:
    with pytest.raises(ValueError):
        TaskStudyActualFact(uuid4(), value, 0, ())
    with pytest.raises(ValueError):
        PlannedActualFacts((), value, ())
