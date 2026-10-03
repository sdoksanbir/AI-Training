from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from educoach.models import (
    ContextType,
    Goal,
    Learner,
    LearningContext,
    PlanType,
    StudyPlan,
    StudySession,
    StudyTask,
    TaskType,
    TaskStatus,
)
from educoach.persistence import (
    create_schema,
    create_session_factory,
    create_sqlite_engine,
)
from educoach.repositories import GoalRepository, StudyRepository
from educoach.services import LearnerMemoryService


@pytest.fixture
def session_factory_fixture() -> sessionmaker[Session]:
    engine = create_sqlite_engine(
        "sqlite+pysqlite:///:memory:"
    )
    create_schema(engine)

    factory = create_session_factory(engine)

    yield factory

    engine.dispose()


def register_learner_with_two_contexts(
    factory: sessionmaker[Session],
) -> tuple[Learner, LearningContext, LearningContext]:
    learner = Learner()

    school_context = LearningContext(
        learner_id=learner.learner_id,
        context_type=ContextType.SCHOOL,
        program_code="school_11",
        grade_level=11,
    )

    exam_context = LearningContext(
        learner_id=learner.learner_id,
        context_type=ContextType.ENTRANCE_EXAM,
        program_code="yks",
    )

    LearnerMemoryService(factory).register_learner(
        learner,
        [school_context, exam_context],
    )

    return learner, school_context, exam_context


def test_save_study_plan_commits_plan_and_tasks_together(
    session_factory_fixture: sessionmaker[Session],
) -> None:
    learner, school_context, exam_context = (
        register_learner_with_two_contexts(
            session_factory_fixture
        )
    )

    plan = StudyPlan(
        learner_id=learner.learner_id,
        title="Karma haftalÄ±k plan",
        plan_type=PlanType.WEEKLY,
        start_date=date(2026, 10, 5),
        end_date=date(2026, 10, 11),
    )

    school_task = StudyTask(
        plan_id=plan.plan_id,
        context_id=school_context.context_id,
        task_date=date(2026, 10, 5),
        task_type=TaskType.STUDY,
        description="Okul matematik tekrarÄ±",
        planned_minutes=40,
    )

    exam_task = StudyTask(
        plan_id=plan.plan_id,
        context_id=exam_context.context_id,
        task_date=date(2026, 10, 6),
        task_type=TaskType.PRACTICE,
        description="YKS matematik soru Ã§Ã¶zÃ¼mÃ¼",
        planned_minutes=60,
    )

    service = LearnerMemoryService(
        session_factory_fixture
    )

    service.save_study_plan(
        plan,
        tasks=[school_task, exam_task],
    )

    with session_factory_fixture() as session:
        repository = StudyRepository(session)

        loaded_plan = repository.get_plan(
            plan.plan_id
        )

        loaded_tasks = repository.list_tasks(
            plan.plan_id
        )

    assert loaded_plan is not None
    assert len(loaded_tasks) == 2

    assert {
        task.context_id
        for task in loaded_tasks
    } == {
        school_context.context_id,
        exam_context.context_id,
    }


def test_save_study_plan_rejects_task_for_another_plan(
    session_factory_fixture: sessionmaker[Session],
) -> None:
    learner, school_context, _ = (
        register_learner_with_two_contexts(
            session_factory_fixture
        )
    )

    plan = StudyPlan(
        learner_id=learner.learner_id,
        title="Plan",
        plan_type=PlanType.DAILY,
        start_date=date(2026, 10, 5),
        end_date=date(2026, 10, 5),
    )

    task = StudyTask(
        plan_id=uuid4(),
        context_id=school_context.context_id,
        task_date=date(2026, 10, 5),
        task_type=TaskType.STUDY,
        description="YanlÄ±ÅŸ plan gÃ¶revi",
        planned_minutes=30,
    )

    service = LearnerMemoryService(
        session_factory_fixture
    )

    with pytest.raises(ValueError):
        service.save_study_plan(
            plan,
            tasks=[task],
        )

    with session_factory_fixture() as session:
        loaded = StudyRepository(
            session
        ).get_plan(plan.plan_id)

    assert loaded is None


def test_save_study_plan_rejects_task_outside_plan_date_range(
    session_factory_fixture: sessionmaker[Session],
) -> None:
    learner, school_context, _ = (
        register_learner_with_two_contexts(
            session_factory_fixture
        )
    )

    plan = StudyPlan(
        learner_id=learner.learner_id,
        title="HaftalÄ±k plan",
        plan_type=PlanType.WEEKLY,
        start_date=date(2026, 10, 5),
        end_date=date(2026, 10, 11),
    )

    task = StudyTask(
        plan_id=plan.plan_id,
        context_id=school_context.context_id,
        task_date=date(2026, 10, 12),
        task_type=TaskType.STUDY,
        description="Plan dÄ±ÅŸÄ± gÃ¶rev",
        planned_minutes=30,
    )

    with pytest.raises(ValueError):
        LearnerMemoryService(
            session_factory_fixture
        ).save_study_plan(
            plan,
            tasks=[task],
        )

    with session_factory_fixture() as session:
        loaded = StudyRepository(
            session
        ).get_plan(plan.plan_id)

    assert loaded is None


def test_context_specific_plan_rejects_task_from_another_context(
    session_factory_fixture: sessionmaker[Session],
) -> None:
    learner, school_context, exam_context = (
        register_learner_with_two_contexts(
            session_factory_fixture
        )
    )

    plan = StudyPlan(
        learner_id=learner.learner_id,
        context_id=school_context.context_id,
        title="Okul planÄ±",
        plan_type=PlanType.DAILY,
        start_date=date(2026, 10, 5),
        end_date=date(2026, 10, 5),
    )

    task = StudyTask(
        plan_id=plan.plan_id,
        context_id=exam_context.context_id,
        task_date=date(2026, 10, 5),
        task_type=TaskType.PRACTICE,
        description="YKS gÃ¶revi",
        planned_minutes=45,
    )

    with pytest.raises(ValueError):
        LearnerMemoryService(
            session_factory_fixture
        ).save_study_plan(
            plan,
            tasks=[task],
        )

    with session_factory_fixture() as session:
        loaded = StudyRepository(
            session
        ).get_plan(plan.plan_id)

    assert loaded is None


def test_save_study_plan_rolls_back_everything_when_task_insert_fails(
    session_factory_fixture: sessionmaker[Session],
) -> None:
    learner, school_context, _ = (
        register_learner_with_two_contexts(
            session_factory_fixture
        )
    )

    plan = StudyPlan(
        learner_id=learner.learner_id,
        title="GÃ¼nlÃ¼k plan",
        plan_type=PlanType.DAILY,
        start_date=date(2026, 10, 5),
        end_date=date(2026, 10, 5),
    )

    duplicated_task_id = uuid4()

    first_task = StudyTask(
        task_id=duplicated_task_id,
        plan_id=plan.plan_id,
        context_id=school_context.context_id,
        task_date=date(2026, 10, 5),
        task_type=TaskType.STUDY,
        description="Birinci gÃ¶rev",
        planned_minutes=30,
    )

    second_task = StudyTask(
        task_id=duplicated_task_id,
        plan_id=plan.plan_id,
        context_id=school_context.context_id,
        task_date=date(2026, 10, 5),
        task_type=TaskType.PRACTICE,
        description="Ä°kinci gÃ¶rev",
        planned_minutes=45,
    )

    service = LearnerMemoryService(
        session_factory_fixture
    )

    with pytest.raises(IntegrityError):
        service.save_study_plan(
            plan,
            tasks=[first_task, second_task],
        )

    with session_factory_fixture() as session:
        repository = StudyRepository(session)

        loaded_plan = repository.get_plan(
            plan.plan_id
        )

        loaded_tasks = repository.list_tasks(
            plan.plan_id
        )

    assert loaded_plan is None
    assert loaded_tasks == []



def test_context_specific_plan_rejects_goal_from_another_context(
    session_factory_fixture: sessionmaker[Session],
) -> None:
    learner, school_context, exam_context = (
        register_learner_with_two_contexts(
            session_factory_fixture
        )
    )

    goal = Goal(
        learner_id=learner.learner_id,
        context_id=exam_context.context_id,
        goal_type="exam_target",
        description="YKS hedefi",
        target_value=80,
        target_unit="net",
    )

    with session_factory_fixture() as session:
        with session.begin():
            GoalRepository(session).add(goal)

    plan = StudyPlan(
        learner_id=learner.learner_id,
        context_id=school_context.context_id,
        goal_id=goal.goal_id,
        title="Okul çalışma planı",
        plan_type=PlanType.DAILY,
        start_date=date(2026, 10, 5),
        end_date=date(2026, 10, 5),
    )

    service = LearnerMemoryService(
        session_factory_fixture
    )

    with pytest.raises(ValueError):
        service.save_study_plan(plan)

    with session_factory_fixture() as session:
        loaded = StudyRepository(
            session
        ).get_plan(plan.plan_id)

    assert loaded is None


def test_record_study_session_commits_session_for_existing_task(
    session_factory_fixture: sessionmaker[Session],
) -> None:
    learner, context, _ = register_learner_with_two_contexts(
        session_factory_fixture
    )
    plan = StudyPlan(
        learner_id=learner.learner_id,
        title="Günlük plan",
        plan_type=PlanType.DAILY,
        start_date=date(2026, 10, 5),
        end_date=date(2026, 10, 5),
    )
    task = StudyTask(
        plan_id=plan.plan_id,
        context_id=context.context_id,
        task_date=date(2026, 10, 5),
        task_type=TaskType.STUDY,
        description="Matematik",
        planned_minutes=60,
    )
    service = LearnerMemoryService(session_factory_fixture)
    service.save_study_plan(plan, [task])

    study_session = StudySession(
        learner_id=learner.learner_id,
        context_id=context.context_id,
        task_id=task.task_id,
        duration_minutes=42,
        completion_level=1,
        learner_note="Konu tekrarını tamamladım",
    )
    service.record_study_session(study_session)

    with session_factory_fixture() as session:
        loaded = StudyRepository(session).get_session(study_session.session_id)

    assert loaded is not None
    assert loaded.duration_minutes == 42
    assert loaded.task_id == task.task_id

    with session_factory_fixture() as session:
        loaded_task = StudyRepository(session).get_task(task.task_id)

    assert loaded_task is not None
    assert loaded_task.status == TaskStatus.COMPLETED
    assert loaded_task.completed_at is not None


def test_record_study_session_rejects_wrong_task_context(
    session_factory_fixture: sessionmaker[Session],
) -> None:
    learner, school_context, exam_context = register_learner_with_two_contexts(
        session_factory_fixture
    )
    plan = StudyPlan(
        learner_id=learner.learner_id,
        title="Karma plan",
        plan_type=PlanType.DAILY,
        start_date=date(2026, 10, 5),
        end_date=date(2026, 10, 5),
    )
    task = StudyTask(
        plan_id=plan.plan_id,
        context_id=school_context.context_id,
        task_date=date(2026, 10, 5),
        task_type=TaskType.STUDY,
        description="Matematik",
        planned_minutes=30,
    )
    service = LearnerMemoryService(session_factory_fixture)
    service.save_study_plan(plan, [task])

    invalid_session = StudySession(
        learner_id=learner.learner_id,
        context_id=exam_context.context_id,
        task_id=task.task_id,
        duration_minutes=20,
    )

    with pytest.raises(ValueError):
        service.record_study_session(invalid_session)

    with session_factory_fixture() as session:
        assert StudyRepository(session).get_session(invalid_session.session_id) is None


def test_get_learner_memory_summary_collects_core_memory(
    session_factory_fixture: sessionmaker[Session],
) -> None:
    learner, context, _ = register_learner_with_two_contexts(
        session_factory_fixture
    )
    plan = StudyPlan(
        learner_id=learner.learner_id,
        title="Özet planı",
        plan_type=PlanType.DAILY,
        start_date=date(2026, 10, 5),
        end_date=date(2026, 10, 5),
    )
    LearnerMemoryService(session_factory_fixture).save_study_plan(plan)

    summary = LearnerMemoryService(
        session_factory_fixture
    ).get_learner_memory_summary(learner.learner_id)

    assert summary["learner"].learner_id == learner.learner_id
    assert len(summary["contexts"]) == 2
    assert summary["goals"] == []
    assert summary["assessments"] == []
    assert summary["assessment_results"] == {}
    assert summary["study_plans"][0].plan_id == plan.plan_id
