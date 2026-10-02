from datetime import date, datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

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
)
from educoach.persistence import (
    create_schema,
    create_session_factory,
    create_sqlite_engine,
)
from educoach.repositories import (
    GoalRepository,
    LearnerRepository,
    StudyRepository,
)


@pytest.fixture
def session() -> Session:
    engine = create_sqlite_engine(
        "sqlite+pysqlite:///:memory:"
    )
    create_schema(engine)

    factory = create_session_factory(engine)

    with factory() as session:
        yield session

    engine.dispose()


def make_learner_context(
    session: Session,
) -> tuple[Learner, LearningContext]:
    learner = Learner()

    context = LearningContext(
        learner_id=learner.learner_id,
        context_type=ContextType.SCHOOL,
        program_code="school_11",
        grade_level=11,
    )

    repository = LearnerRepository(session)
    repository.add_learner(learner)
    repository.add_context(context)

    return learner, context


def test_plan_without_context_round_trip(
    session: Session,
) -> None:
    learner = Learner()
    LearnerRepository(session).add_learner(learner)

    plan = StudyPlan(
        learner_id=learner.learner_id,
        title="Karma günlük plan",
        plan_type=PlanType.DAILY,
        start_date=date(2026, 10, 3),
        end_date=date(2026, 10, 3),
    )

    repository = StudyRepository(session)
    repository.add_plan(plan)
    session.commit()

    loaded = repository.get_plan(plan.plan_id)

    assert loaded is not None
    assert loaded.context_id is None
    assert loaded.title == "Karma günlük plan"


def test_plan_with_context_round_trip(
    session: Session,
) -> None:
    learner, context = make_learner_context(session)

    plan = StudyPlan(
        learner_id=learner.learner_id,
        context_id=context.context_id,
        title="Okul planı",
        plan_type=PlanType.WEEKLY,
        start_date=date(2026, 10, 5),
        end_date=date(2026, 10, 11),
    )

    repository = StudyRepository(session)
    repository.add_plan(plan)
    session.commit()

    loaded = repository.get_plan(plan.plan_id)

    assert loaded is not None
    assert loaded.context_id == context.context_id


def test_plan_cannot_use_another_learners_context(
    session: Session,
) -> None:
    first = Learner()
    second = Learner()

    second_context = LearningContext(
        learner_id=second.learner_id,
        context_type=ContextType.SCHOOL,
        program_code="school_8",
        grade_level=8,
    )

    learners = LearnerRepository(session)
    learners.add_learner(first)
    learners.add_learner(second)
    learners.add_context(second_context)

    plan = StudyPlan(
        learner_id=first.learner_id,
        context_id=second_context.context_id,
        title="Geçersiz plan",
        plan_type=PlanType.DAILY,
        start_date=date(2026, 10, 3),
        end_date=date(2026, 10, 3),
    )

    with pytest.raises(IntegrityError):
        StudyRepository(session).add_plan(plan)

    session.rollback()


def test_plan_cannot_use_another_learners_goal(
    session: Session,
) -> None:
    first = Learner()
    second = Learner()

    learners = LearnerRepository(session)
    learners.add_learner(first)
    learners.add_learner(second)

    goal = Goal(
        learner_id=second.learner_id,
        goal_type="routine",
        description="İkinci öğrenenin hedefi",
    )

    GoalRepository(session).add(goal)

    plan = StudyPlan(
        learner_id=first.learner_id,
        goal_id=goal.goal_id,
        title="Geçersiz hedef bağlantısı",
        plan_type=PlanType.DAILY,
        start_date=date(2026, 10, 3),
        end_date=date(2026, 10, 3),
    )

    with pytest.raises(IntegrityError):
        StudyRepository(session).add_plan(plan)

    session.rollback()


def test_task_round_trip_keeps_planned_minutes(
    session: Session,
) -> None:
    learner, context = make_learner_context(session)

    plan = StudyPlan(
        learner_id=learner.learner_id,
        title="Günlük plan",
        plan_type=PlanType.DAILY,
        start_date=date(2026, 10, 3),
        end_date=date(2026, 10, 3),
    )

    repository = StudyRepository(session)
    repository.add_plan(plan)

    task = StudyTask(
        plan_id=plan.plan_id,
        context_id=context.context_id,
        task_date=date(2026, 10, 3),
        task_type=TaskType.PRACTICE,
        description="Matematik soru çözümü",
        planned_minutes=60,
    )

    repository.add_task(task)
    session.commit()

    loaded = repository.get_task(task.task_id)

    assert loaded is not None
    assert loaded.planned_minutes == 60
    assert loaded.context_id == context.context_id


def test_task_context_must_belong_to_plan_learner(
    session: Session,
) -> None:
    first = Learner()
    second = Learner()

    first_context = LearningContext(
        learner_id=first.learner_id,
        context_type=ContextType.SCHOOL,
        program_code="school_11",
        grade_level=11,
    )

    second_context = LearningContext(
        learner_id=second.learner_id,
        context_type=ContextType.SCHOOL,
        program_code="school_8",
        grade_level=8,
    )

    learners = LearnerRepository(session)
    learners.add_learner(first)
    learners.add_learner(second)
    learners.add_context(first_context)
    learners.add_context(second_context)

    plan = StudyPlan(
        learner_id=first.learner_id,
        title="Birinci öğrenenin planı",
        plan_type=PlanType.DAILY,
        start_date=date(2026, 10, 3),
        end_date=date(2026, 10, 3),
    )

    repository = StudyRepository(session)
    repository.add_plan(plan)

    task = StudyTask(
        plan_id=plan.plan_id,
        context_id=second_context.context_id,
        task_date=date(2026, 10, 3),
        task_type=TaskType.STUDY,
        description="Geçersiz görev",
        planned_minutes=30,
    )

    with pytest.raises(IntegrityError):
        repository.add_task(task)

    session.rollback()


def test_task_requires_existing_plan(
    session: Session,
) -> None:
    _, context = make_learner_context(session)

    task = StudyTask(
        plan_id=__import__("uuid").uuid4(),
        context_id=context.context_id,
        task_date=date(2026, 10, 3),
        task_type=TaskType.STUDY,
        description="Plansız görev",
        planned_minutes=30,
    )

    with pytest.raises(ValueError):
        StudyRepository(session).add_task(task)


def test_session_keeps_actual_duration_separate(
    session: Session,
) -> None:
    learner, context = make_learner_context(session)

    repository = StudyRepository(session)

    plan = StudyPlan(
        learner_id=learner.learner_id,
        title="Günlük plan",
        plan_type=PlanType.DAILY,
        start_date=date(2026, 10, 3),
        end_date=date(2026, 10, 3),
    )

    repository.add_plan(plan)

    task = StudyTask(
        plan_id=plan.plan_id,
        context_id=context.context_id,
        task_date=date(2026, 10, 3),
        task_type=TaskType.PRACTICE,
        description="Matematik",
        planned_minutes=60,
    )

    repository.add_task(task)

    study_session = StudySession(
        learner_id=learner.learner_id,
        context_id=context.context_id,
        task_id=task.task_id,
        duration_minutes=35,
    )

    repository.add_session(study_session)
    session.commit()

    loaded = repository.get_session(
        study_session.session_id
    )

    assert loaded is not None
    assert task.planned_minutes == 60
    assert loaded.duration_minutes == 35


def test_session_task_must_belong_to_same_learner(
    session: Session,
) -> None:
    first, first_context = make_learner_context(session)

    second = Learner()
    second_context = LearningContext(
        learner_id=second.learner_id,
        context_type=ContextType.SCHOOL,
        program_code="school_8",
        grade_level=8,
    )

    learners = LearnerRepository(session)
    learners.add_learner(second)
    learners.add_context(second_context)

    repository = StudyRepository(session)

    plan = StudyPlan(
        learner_id=first.learner_id,
        title="Birinci plan",
        plan_type=PlanType.DAILY,
        start_date=date(2026, 10, 3),
        end_date=date(2026, 10, 3),
    )
    repository.add_plan(plan)

    task = StudyTask(
        plan_id=plan.plan_id,
        context_id=first_context.context_id,
        task_date=date(2026, 10, 3),
        task_type=TaskType.STUDY,
        description="Birinci görev",
        planned_minutes=30,
    )
    repository.add_task(task)

    invalid_session = StudySession(
        learner_id=second.learner_id,
        context_id=second_context.context_id,
        task_id=task.task_id,
        duration_minutes=20,
    )

    with pytest.raises(IntegrityError):
        repository.add_session(invalid_session)

    session.rollback()


def test_session_task_must_belong_to_same_context(
    session: Session,
) -> None:
    learner = Learner()

    first_context = LearningContext(
        learner_id=learner.learner_id,
        context_type=ContextType.SCHOOL,
        program_code="school_11",
        grade_level=11,
    )

    second_context = LearningContext(
        learner_id=learner.learner_id,
        context_type=ContextType.ENTRANCE_EXAM,
        program_code="yks",
    )

    learners = LearnerRepository(session)
    learners.add_learner(learner)
    learners.add_context(first_context)
    learners.add_context(second_context)

    repository = StudyRepository(session)

    plan = StudyPlan(
        learner_id=learner.learner_id,
        title="Karma plan",
        plan_type=PlanType.DAILY,
        start_date=date(2026, 10, 3),
        end_date=date(2026, 10, 3),
    )
    repository.add_plan(plan)

    task = StudyTask(
        plan_id=plan.plan_id,
        context_id=first_context.context_id,
        task_date=date(2026, 10, 3),
        task_type=TaskType.STUDY,
        description="Okul görevi",
        planned_minutes=30,
    )
    repository.add_task(task)

    invalid_session = StudySession(
        learner_id=learner.learner_id,
        context_id=second_context.context_id,
        task_id=task.task_id,
        duration_minutes=20,
    )

    with pytest.raises(IntegrityError):
        repository.add_session(invalid_session)

    session.rollback()


def test_session_without_task_is_allowed(
    session: Session,
) -> None:
    learner, context = make_learner_context(session)

    study_session = StudySession(
        learner_id=learner.learner_id,
        context_id=context.context_id,
        duration_minutes=25,
        learner_note="Plansız tekrar yaptım",
    )

    repository = StudyRepository(session)
    repository.add_session(study_session)
    session.commit()

    loaded = repository.get_session(
        study_session.session_id
    )

    assert loaded is not None
    assert loaded.task_id is None
    assert loaded.duration_minutes == 25
