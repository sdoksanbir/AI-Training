from dataclasses import FrozenInstanceError
from datetime import date
from uuid import UUID, uuid4

import pytest

from educoach.models import (
    ContextStatus,
    ContextType,
    Goal,
    GoalStatus,
    Learner,
    LearningContext,
    PlanStatus,
    PlanType,
    StudyPlan,
)
from educoach.orchestrator import (
    ContextSelectionEvidence,
    ContextSelectionEvidenceStatus,
    project_context_selection_evidence,
)
from educoach.services import LearnerMemorySnapshot


def make_context(
    learner: Learner,
    *,
    context_id: UUID | None = None,
    status: ContextStatus = ContextStatus.ACTIVE,
) -> LearningContext:
    values = {
        "learner_id": learner.learner_id,
        "context_type": ContextType.SCHOOL,
        "program_code": "school_11",
        "status": status,
    }
    if context_id is not None:
        values["context_id"] = context_id
    return LearningContext(**values)


def make_goal(
    learner: Learner,
    context_id: UUID | None,
    *,
    status: GoalStatus = GoalStatus.ACTIVE,
) -> Goal:
    return Goal(
        learner_id=learner.learner_id,
        context_id=context_id,
        goal_type="study",
        description="Çalışma hedefi",
        status=status,
    )


def make_plan(
    learner: Learner,
    context_id: UUID | None,
    *,
    status: PlanStatus = PlanStatus.ACTIVE,
) -> StudyPlan:
    return StudyPlan(
        learner_id=learner.learner_id,
        context_id=context_id,
        title="Çalışma planı",
        plan_type=PlanType.WEEKLY,
        start_date=date(2026, 10, 5),
        end_date=date(2026, 10, 11),
        status=status,
    )


def make_snapshot(
    learner: Learner,
    contexts: tuple[LearningContext, ...] = (),
    *,
    goals: tuple[Goal, ...] = (),
    plans: tuple[StudyPlan, ...] = (),
) -> LearnerMemorySnapshot:
    return LearnerMemorySnapshot(
        learner=learner,
        contexts=contexts,
        goals=goals,
        availability=(),
        assessments=(),
        assessment_results=(),
        learning_evidence=(),
        study_plans=plans,
        study_tasks=(),
        study_sessions=(),
        preferences=(),
        coaching_states=(),
    )


def test_no_context_has_no_evidence() -> None:
    learner = Learner()

    result = project_context_selection_evidence(make_snapshot(learner))

    assert result == ContextSelectionEvidence(
        ContextSelectionEvidenceStatus.NONE, (), (), ()
    )


def test_active_context_without_goal_or_plan_has_no_evidence() -> None:
    learner = Learner()
    context = make_context(learner)

    assert project_context_selection_evidence(
        make_snapshot(learner, (context,))
    ).status == ContextSelectionEvidenceStatus.NONE


def test_active_goal_is_consistent_evidence() -> None:
    learner = Learner()
    context = make_context(learner)
    goal = make_goal(learner, context.context_id)

    result = project_context_selection_evidence(
        make_snapshot(learner, (context,), goals=(goal,))
    )

    assert result.status == ContextSelectionEvidenceStatus.CONSISTENT
    assert result.active_goal_context_ids == (context.context_id,)
    assert result.candidate_context_ids == (context.context_id,)


def test_active_plan_is_consistent_evidence() -> None:
    learner = Learner()
    context = make_context(learner)
    plan = make_plan(learner, context.context_id)

    result = project_context_selection_evidence(
        make_snapshot(learner, (context,), plans=(plan,))
    )

    assert result.status == ContextSelectionEvidenceStatus.CONSISTENT
    assert result.active_plan_context_ids == (context.context_id,)


def test_goal_and_plan_for_same_context_are_consistent() -> None:
    learner = Learner()
    context = make_context(learner)

    result = project_context_selection_evidence(
        make_snapshot(
            learner,
            (context,),
            goals=(make_goal(learner, context.context_id),),
            plans=(make_plan(learner, context.context_id),),
        )
    )

    assert result.status == ContextSelectionEvidenceStatus.CONSISTENT
    assert result.candidate_context_ids == (context.context_id,)


def test_goal_and_plan_for_different_contexts_conflict() -> None:
    learner = Learner()
    first = make_context(learner)
    second = make_context(learner)

    result = project_context_selection_evidence(
        make_snapshot(
            learner,
            (first, second),
            goals=(make_goal(learner, first.context_id),),
            plans=(make_plan(learner, second.context_id),),
        )
    )

    assert result.status == ContextSelectionEvidenceStatus.CONFLICTING
    assert set(result.candidate_context_ids) == {
        first.context_id,
        second.context_id,
    }


@pytest.mark.parametrize("source", ["goal", "plan"])
def test_two_active_records_for_different_contexts_conflict(source: str) -> None:
    learner = Learner()
    first = make_context(learner)
    second = make_context(learner)
    kwargs = (
        {
            "goals": (
                make_goal(learner, first.context_id),
                make_goal(learner, second.context_id),
            )
        }
        if source == "goal"
        else {
            "plans": (
                make_plan(learner, first.context_id),
                make_plan(learner, second.context_id),
            )
        }
    )

    result = project_context_selection_evidence(
        make_snapshot(learner, (first, second), **kwargs)
    )

    assert result.status == ContextSelectionEvidenceStatus.CONFLICTING


@pytest.mark.parametrize("source", ["goal", "plan"])
def test_repeated_active_records_do_not_duplicate_context(source: str) -> None:
    learner = Learner()
    context = make_context(learner)
    records = (
        (
            make_goal(learner, context.context_id),
            make_goal(learner, context.context_id),
        )
        if source == "goal"
        else (
            make_plan(learner, context.context_id),
            make_plan(learner, context.context_id),
        )
    )
    kwargs = {"goals" if source == "goal" else "plans": records}

    result = project_context_selection_evidence(
        make_snapshot(learner, (context,), **kwargs)
    )

    assert result.candidate_context_ids == (context.context_id,)


@pytest.mark.parametrize(
    "status",
    [GoalStatus.PAUSED, GoalStatus.COMPLETED, GoalStatus.CANCELLED],
)
def test_non_active_goal_is_not_evidence(status: GoalStatus) -> None:
    learner = Learner()
    context = make_context(learner)

    result = project_context_selection_evidence(
        make_snapshot(
            learner,
            (context,),
            goals=(make_goal(learner, context.context_id, status=status),),
        )
    )

    assert result.status == ContextSelectionEvidenceStatus.NONE


@pytest.mark.parametrize(
    "status",
    [PlanStatus.DRAFT, PlanStatus.COMPLETED, PlanStatus.CANCELLED],
)
def test_non_active_plan_is_not_evidence(status: PlanStatus) -> None:
    learner = Learner()
    context = make_context(learner)

    result = project_context_selection_evidence(
        make_snapshot(
            learner,
            (context,),
            plans=(make_plan(learner, context.context_id, status=status),),
        )
    )

    assert result.status == ContextSelectionEvidenceStatus.NONE


def test_unscoped_goal_and_plan_are_not_evidence() -> None:
    learner = Learner()
    context = make_context(learner)

    result = project_context_selection_evidence(
        make_snapshot(
            learner,
            (context,),
            goals=(make_goal(learner, None),),
            plans=(make_plan(learner, None),),
        )
    )

    assert result.status == ContextSelectionEvidenceStatus.NONE


@pytest.mark.parametrize(
    ("context_status", "source"),
    [
        (ContextStatus.INACTIVE, "goal"),
        (ContextStatus.COMPLETED, "plan"),
    ],
)
def test_non_active_context_cannot_produce_routing_evidence(
    context_status: ContextStatus,
    source: str,
) -> None:
    learner = Learner()
    context = make_context(learner, status=context_status)
    kwargs = (
        {"goals": (make_goal(learner, context.context_id),)}
        if source == "goal"
        else {"plans": (make_plan(learner, context.context_id),)}
    )

    result = project_context_selection_evidence(
        make_snapshot(learner, (context,), **kwargs)
    )

    assert result.status == ContextSelectionEvidenceStatus.NONE


@pytest.mark.parametrize("source", ["goal", "plan"])
def test_foreign_learner_record_is_rejected(source: str) -> None:
    learner = Learner()
    context = make_context(learner)
    foreign = Learner()
    kwargs = (
        {"goals": (make_goal(foreign, context.context_id),)}
        if source == "goal"
        else {"plans": (make_plan(foreign, context.context_id),)}
    )

    with pytest.raises(ValueError, match="snapshot learner"):
        project_context_selection_evidence(
            make_snapshot(learner, (context,), **kwargs)
        )


@pytest.mark.parametrize("source", ["goal", "plan"])
def test_unknown_context_reference_is_rejected(source: str) -> None:
    learner = Learner()
    context = make_context(learner)
    unknown_context_id = uuid4()
    kwargs = (
        {"goals": (make_goal(learner, unknown_context_id),)}
        if source == "goal"
        else {"plans": (make_plan(learner, unknown_context_id),)}
    )

    with pytest.raises(ValueError, match="snapshot context"):
        project_context_selection_evidence(
            make_snapshot(learner, (context,), **kwargs)
        )


def test_duplicate_context_id_is_rejected_before_projection() -> None:
    learner = Learner()
    context_id = uuid4()

    with pytest.raises(ValueError, match="duplicate context_id"):
        project_context_selection_evidence(
            make_snapshot(
                learner,
                (
                    make_context(learner, context_id=context_id),
                    make_context(learner, context_id=context_id),
                ),
            )
        )


def test_foreign_context_is_rejected_before_projection() -> None:
    learner = Learner()

    with pytest.raises(ValueError, match="snapshot learner"):
        project_context_selection_evidence(
            make_snapshot(learner, (make_context(Learner()),))
        )


def test_input_order_does_not_change_result_and_ids_are_canonical() -> None:
    learner = Learner()
    later = make_context(learner, context_id=UUID(int=2))
    earlier = make_context(learner, context_id=UUID(int=1))
    goals = (
        make_goal(learner, later.context_id),
        make_goal(learner, earlier.context_id),
    )

    forward = project_context_selection_evidence(
        make_snapshot(learner, (later, earlier), goals=goals)
    )
    reverse = project_context_selection_evidence(
        make_snapshot(
            learner,
            (earlier, later),
            goals=tuple(reversed(goals)),
        )
    )

    assert forward == reverse
    assert forward.candidate_context_ids == (
        earlier.context_id,
        later.context_id,
    )


def test_result_is_immutable() -> None:
    result = ContextSelectionEvidence(
        ContextSelectionEvidenceStatus.NONE, (), (), ()
    )

    with pytest.raises(FrozenInstanceError):
        result.status = ContextSelectionEvidenceStatus.CONSISTENT


@pytest.mark.parametrize(
    ("status", "candidates", "goals", "plans"),
    [
        (ContextSelectionEvidenceStatus.CONSISTENT, (), (), ()),
        (
            ContextSelectionEvidenceStatus.NONE,
            (UUID(int=1),),
            (UUID(int=1),),
            (),
        ),
        (
            ContextSelectionEvidenceStatus.CONFLICTING,
            (UUID(int=1),),
            (UUID(int=1),),
            (),
        ),
        (
            ContextSelectionEvidenceStatus.NONE,
            (UUID(int=1), UUID(int=2)),
            (UUID(int=2), UUID(int=1)),
            (),
        ),
    ],
)
def test_invalid_direct_contract_state_is_rejected(
    status: ContextSelectionEvidenceStatus,
    candidates: tuple[UUID, ...],
    goals: tuple[UUID, ...],
    plans: tuple[UUID, ...],
) -> None:
    with pytest.raises(ValueError):
        ContextSelectionEvidence(status, candidates, goals, plans)
