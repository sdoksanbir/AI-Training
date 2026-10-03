from datetime import date
from uuid import uuid4

import pytest

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
from educoach.rules import (
    KnownFactKind,
    TimeBudgetResolutionStatus,
    project_known_facts,
)
from educoach.services.snapshot import LearnerMemorySnapshot


TARGET_DATE = date(2026, 10, 5)


def empty_snapshot(learner: Learner, **overrides) -> LearnerMemorySnapshot:
    values = {
        "learner": learner,
        "contexts": (),
        "goals": (),
        "availability": (),
        "assessments": (),
        "assessment_results": (),
        "learning_evidence": (),
        "study_plans": (),
        "study_tasks": (),
        "study_sessions": (),
        "preferences": (),
        "coaching_states": (),
    }
    values.update(overrides)
    return LearnerMemorySnapshot(**values)


def make_context(learner: Learner) -> LearningContext:
    return LearningContext(
        learner_id=learner.learner_id,
        context_type=ContextType.ENTRANCE_EXAM,
        program_code="yks",
        grade_level=12,
    )


def test_exact_recorded_learner_context_and_goal_facts_are_preserved() -> None:
    learner = Learner(display_name="Ada", preferred_language="tr")
    context = make_context(learner)
    goal = Goal(
        learner_id=learner.learner_id,
        context_id=context.context_id,
        goal_type="exam_target",
        description="YKS hazırlığı",
        target_value=80,
        target_unit="net",
    )

    facts = project_known_facts(
        empty_snapshot(learner, contexts=(context,), goals=(goal,)),
        TARGET_DATE,
    )

    assert facts.learner.display_name == "Ada"
    assert facts.learner.kind == KnownFactKind.EXPLICIT
    assert facts.contexts[0].program_code == "yks"
    assert facts.contexts[0].grade_level == 12
    assert facts.goals[0].target_value == 80
    assert facts.goals[0].target_unit == "net"


def test_missing_data_remains_empty_and_is_not_fabricated() -> None:
    facts = project_known_facts(empty_snapshot(Learner()), TARGET_DATE)

    assert facts.contexts == ()
    assert facts.goals == ()
    assert facts.preferences == ()
    assert facts.learning_evidence == ()
    assert facts.coaching_states == ()
    assert facts.assessments.assessments == ()
    assert facts.planned_actual.task_facts == ()


def test_unknown_availability_has_no_definite_minutes() -> None:
    facts = project_known_facts(empty_snapshot(Learner()), TARGET_DATE)

    assert facts.availability.status == TimeBudgetResolutionStatus.UNKNOWN
    assert facts.availability.available_minutes is None
    assert facts.availability.kind == KnownFactKind.UNCERTAIN


def test_resolved_availability_is_explicitly_derived() -> None:
    learner = Learner()
    availability = Availability(
        learner_id=learner.learner_id,
        day_of_week=DayOfWeek.MONDAY,
        availability_type=AvailabilityType.AVAILABLE,
        available_minutes=120,
    )

    facts = project_known_facts(
        empty_snapshot(learner, availability=(availability,)),
        TARGET_DATE,
    )

    assert facts.availability.available_minutes == 120
    assert facts.availability.kind == KnownFactKind.DERIVED


def test_planned_and_actual_facts_remain_separate() -> None:
    learner = Learner()
    context = make_context(learner)
    plan = StudyPlan(
        learner_id=learner.learner_id,
        context_id=context.context_id,
        title="Plan",
        plan_type=PlanType.DAILY,
        start_date=TARGET_DATE,
        end_date=TARGET_DATE,
    )
    task = StudyTask(
        plan_id=plan.plan_id,
        context_id=context.context_id,
        task_date=TARGET_DATE,
        task_type=TaskType.STUDY,
        description="Matematik",
        planned_minutes=60,
    )
    session = StudySession(
        learner_id=learner.learner_id,
        context_id=context.context_id,
        task_id=task.task_id,
        duration_minutes=25,
    )

    facts = project_known_facts(
        empty_snapshot(
            learner,
            contexts=(context,),
            study_plans=(plan,),
            study_tasks=(task,),
            study_sessions=(session,),
        ),
        TARGET_DATE,
    )

    task_fact = facts.planned_actual.task_facts[0]
    assert (task_fact.planned_minutes, task_fact.actual_minutes) == (60, 25)
    assert facts.planned_actual_kind == KnownFactKind.DERIVED


def test_taskless_session_outside_snapshot_context_is_rejected() -> None:
    learner = Learner()
    snapshot_context = make_context(learner)
    taskless_session = StudySession(
        learner_id=learner.learner_id,
        context_id=uuid4(),
        duration_minutes=20,
    )

    with pytest.raises(ValueError, match="snapshot context"):
        project_known_facts(
            empty_snapshot(
                learner,
                contexts=(snapshot_context,),
                study_sessions=(taskless_session,),
            ),
            TARGET_DATE,
        )


def test_taskless_session_inside_snapshot_context_remains_valid() -> None:
    learner = Learner()
    context = make_context(learner)
    taskless_session = StudySession(
        learner_id=learner.learner_id,
        context_id=context.context_id,
        duration_minutes=20,
    )

    facts = project_known_facts(
        empty_snapshot(
            learner,
            contexts=(context,),
            study_sessions=(taskless_session,),
        ),
        TARGET_DATE,
    )

    assert facts.planned_actual.unassigned_actual_minutes == 20
    assert facts.planned_actual.unassigned_session_ids == (
        taskless_session.session_id,
    )


def test_assessment_truth_contains_only_recorded_result() -> None:
    learner = Learner()
    context = make_context(learner)
    assessment = Assessment(
        learner_id=learner.learner_id,
        context_id=context.context_id,
        assessment_type="mock_exam",
        assessment_name="TYT",
        assessment_date=TARGET_DATE,
    )
    result = AssessmentResult(assessment_id=assessment.assessment_id, net=74)

    facts = project_known_facts(
        empty_snapshot(
            learner,
            contexts=(context,),
            assessments=(assessment,),
            assessment_results=(result,),
        ),
        TARGET_DATE,
    )

    recorded = facts.assessments.assessments[0].results[0]
    assert recorded.net == 74
    assert recorded.score is None
    assert recorded.assessment_id == assessment.assessment_id


def test_source_types_preserve_explicit_derived_and_inferred_distinction() -> None:
    learner = Learner()
    context = make_context(learner)
    explicit = Preference(
        learner_id=learner.learner_id,
        context_id=context.context_id,
        preference_key="tone",
        preference_value="concise",
        source_type=EvidenceSource.LEARNER_REPORTED,
    )
    inferred = Preference(
        learner_id=learner.learner_id,
        context_id=context.context_id,
        preference_key="pace",
        preference_value="slow",
        source_type=EvidenceSource.COACH_INFERRED,
    )
    derived = LearningEvidence(
        learner_id=learner.learner_id,
        context_id=context.context_id,
        area_type="subject",
        area_code="mathematics",
        state=EvidenceState.DEVELOPING,
        source_type=EvidenceSource.ASSESSMENT_DERIVED,
        assessment_id=uuid4(),
    )

    facts = project_known_facts(
        empty_snapshot(
            learner,
            contexts=(context,),
            preferences=(explicit, inferred),
            learning_evidence=(derived,),
        ),
        TARGET_DATE,
    )

    kinds = {item.preference_key: item.kind for item in facts.preferences}
    assert kinds == {
        "tone": KnownFactKind.EXPLICIT,
        "pace": KnownFactKind.INFERRED,
    }
    assert facts.learning_evidence[0].kind == KnownFactKind.DERIVED


def test_unknown_evidence_is_marked_uncertain() -> None:
    learner = Learner()
    context = make_context(learner)
    evidence = LearningEvidence(
        learner_id=learner.learner_id,
        context_id=context.context_id,
        area_type="subject",
        area_code="mathematics",
        state=EvidenceState.UNKNOWN,
        source_type=EvidenceSource.LEARNER_REPORTED,
    )

    facts = project_known_facts(
        empty_snapshot(
            learner,
            contexts=(context,),
            learning_evidence=(evidence,),
        ),
        TARGET_DATE,
    )

    assert facts.learning_evidence[0].kind == KnownFactKind.UNCERTAIN


def test_foreign_learner_record_is_rejected() -> None:
    learner = Learner()
    foreign = Learner()
    preference = Preference(
        learner_id=foreign.learner_id,
        preference_key="tone",
        preference_value="concise",
    )

    with pytest.raises(ValueError, match="snapshot learner"):
        project_known_facts(
            empty_snapshot(learner, preferences=(preference,)),
            TARGET_DATE,
        )


def test_record_cannot_cross_context_boundary() -> None:
    learner = Learner()
    context = make_context(learner)
    state = CoachingState(
        learner_id=learner.learner_id,
        context_id=uuid4(),
    )

    with pytest.raises(ValueError, match="snapshot context"):
        project_known_facts(
            empty_snapshot(
                learner,
                contexts=(context,),
                coaching_states=(state,),
            ),
            TARGET_DATE,
        )
