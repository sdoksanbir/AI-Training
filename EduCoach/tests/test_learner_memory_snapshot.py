from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session, sessionmaker

from educoach.models import (
    Assessment,
    AssessmentResult,
    Availability,
    AvailabilityType,
    CoachingState,
    ContextType,
    DayOfWeek,
    EvidenceSource,
    EvidenceState,
    Goal,
    Learner,
    LearningContext,
    LearningEvidence,
    PlanType,
    Preference,
    StudyPlan,
    StudySession,
    StudyTask,
    TaskType,
)
from educoach.persistence import create_schema, create_session_factory, create_sqlite_engine
from educoach.repositories import (
    AssessmentRepository,
    AvailabilityRepository,
    CoachingStateRepository,
    GoalRepository,
    LearnerRepository,
    LearningEvidenceRepository,
    PreferenceRepository,
    StudyRepository,
)
from educoach.services import LearnerMemoryService, LearnerMemorySnapshot


@pytest.fixture
def factory() -> sessionmaker[Session]:
    engine = create_sqlite_engine("sqlite+pysqlite:///:memory:")
    create_schema(engine)
    result = create_session_factory(engine)
    yield result
    engine.dispose()


def seed_full_memory(factory: sessionmaker[Session], name: str):
    learner = Learner(display_name=name)
    context = LearningContext(
        learner_id=learner.learner_id,
        context_type=ContextType.SCHOOL,
        program_code="school_11",
        grade_level=11,
    )
    goal = Goal(
        learner_id=learner.learner_id,
        context_id=context.context_id,
        goal_type="routine",
        description=f"{name} hedefi",
    )
    availability = Availability(
        learner_id=learner.learner_id,
        day_of_week=DayOfWeek.MONDAY,
        availability_type=AvailabilityType.AVAILABLE,
        available_minutes=60,
    )
    assessment = Assessment(
        learner_id=learner.learner_id,
        context_id=context.context_id,
        assessment_type="quiz",
        assessment_name=f"{name} quiz",
        assessment_date=date(2026, 10, 3),
    )
    result = AssessmentResult(assessment_id=assessment.assessment_id, net=8)
    evidence = LearningEvidence(
        learner_id=learner.learner_id,
        context_id=context.context_id,
        area_type="subject",
        area_code="math",
        state=EvidenceState.DEVELOPING,
        source_type=EvidenceSource.LEARNER_REPORTED,
    )
    plan = StudyPlan(
        learner_id=learner.learner_id,
        context_id=context.context_id,
        title=f"{name} plan",
        plan_type=PlanType.DAILY,
        start_date=date(2026, 10, 3),
        end_date=date(2026, 10, 3),
    )
    task = StudyTask(
        plan_id=plan.plan_id,
        context_id=context.context_id,
        task_date=date(2026, 10, 3),
        task_type=TaskType.STUDY,
        description=f"{name} görev",
        planned_minutes=30,
    )
    linked_session = StudySession(
        learner_id=learner.learner_id,
        context_id=context.context_id,
        task_id=task.task_id,
        duration_minutes=20,
    )
    taskless_session = StudySession(
        learner_id=learner.learner_id,
        context_id=context.context_id,
        duration_minutes=10,
    )
    preference = Preference(
        learner_id=learner.learner_id,
        context_id=context.context_id,
        preference_key="explanation_style",
        preference_value="short",
    )
    coaching_state = CoachingState(
        learner_id=learner.learner_id,
        context_id=context.context_id,
        current_focus="math",
    )

    with factory() as session:
        with session.begin():
            learners = LearnerRepository(session)
            learners.add_learner(learner)
            learners.add_context(context)
            GoalRepository(session).add(goal)
            AvailabilityRepository(session).add(availability)
            assessments = AssessmentRepository(session)
            assessments.add_assessment(assessment)
            assessments.add_result(result)
            LearningEvidenceRepository(session).add(evidence)
            studies = StudyRepository(session)
            studies.add_plan(plan)
            studies.add_task(task)
            studies.add_session(linked_session)
            studies.add_session(taskless_session)
            PreferenceRepository(session).add(preference)
            CoachingStateRepository(session).add(coaching_state)

    return learner, taskless_session


def test_snapshot_contains_every_persisted_memory_category(factory) -> None:
    learner, taskless_session = seed_full_memory(factory, "Bir")
    snapshot = LearnerMemoryService(factory).get_learner_memory_snapshot(
        learner.learner_id
    )

    assert isinstance(snapshot, LearnerMemorySnapshot)
    assert all((
        snapshot.contexts,
        snapshot.goals,
        snapshot.availability,
        snapshot.assessments,
        snapshot.assessment_results,
        snapshot.learning_evidence,
        snapshot.study_plans,
        snapshot.study_tasks,
        snapshot.study_sessions,
        snapshot.preferences,
        snapshot.coaching_states,
    ))
    assert taskless_session.session_id in {
        item.session_id for item in snapshot.study_sessions
    }


def test_snapshot_is_strictly_learner_scoped(factory) -> None:
    first, _ = seed_full_memory(factory, "Bir")
    second, _ = seed_full_memory(factory, "İki")
    snapshot = LearnerMemoryService(factory).get_learner_memory_snapshot(
        first.learner_id
    )

    collections = (
        snapshot.contexts,
        snapshot.goals,
        snapshot.availability,
        snapshot.assessments,
        snapshot.learning_evidence,
        snapshot.study_plans,
        snapshot.study_sessions,
        snapshot.preferences,
        snapshot.coaching_states,
    )
    assert all(
        item.learner_id == first.learner_id
        for collection in collections
        for item in collection
    )
    assert second.learner_id != first.learner_id
    first_assessment_ids = {item.assessment_id for item in snapshot.assessments}
    assert all(
        item.assessment_id in first_assessment_ids
        for item in snapshot.assessment_results
    )
    first_plan_ids = {item.plan_id for item in snapshot.study_plans}
    assert all(item.plan_id in first_plan_ids for item in snapshot.study_tasks)


def test_snapshot_unknown_learner_raises(factory) -> None:
    with pytest.raises(ValueError, match="Learner bulunamadı"):
        LearnerMemoryService(factory).get_learner_memory_snapshot(uuid4())


def test_snapshot_empty_categories_are_tuples(factory) -> None:
    learner = Learner()
    LearnerMemoryService(factory).register_learner(learner)
    snapshot = LearnerMemoryService(factory).get_learner_memory_snapshot(
        learner.learner_id
    )
    assert snapshot.contexts == ()
    assert snapshot.study_sessions == ()
    assert snapshot.coaching_states == ()


def test_study_learner_queries_are_isolated_and_keep_taskless_sessions(factory) -> None:
    first, taskless = seed_full_memory(factory, "Bir")
    second, _ = seed_full_memory(factory, "İki")
    with factory() as session:
        repository = StudyRepository(session)
        tasks = repository.list_tasks_for_learner(first.learner_id)
        sessions = repository.list_sessions_for_learner(first.learner_id)

    assert tasks
    assert taskless.session_id in {item.session_id for item in sessions}
    assert all(item.learner_id == first.learner_id for item in sessions)
    assert second.learner_id not in {item.learner_id for item in sessions}
