from dataclasses import FrozenInstanceError
from datetime import date, timedelta
from unittest.mock import Mock
from uuid import uuid4

import pytest

from educoach.models import (
    Availability,
    AvailabilityType,
    ContextType,
    DayOfWeek,
    Goal,
    Learner,
    LearningContext,
    PlanStatus,
    PlanType,
    StudyPlan,
    StudyTask,
    TaskType,
)
from educoach.services import LearnerMemoryService, LearnerMemorySnapshot
from educoach.writeback import (
    StudyPlanWriteProposal,
    WriteValidationStatus,
    validate_study_plan_write,
    write_study_plan_if_valid,
)


MONDAY = date(2026, 10, 5)


def make_context(learner: Learner) -> LearningContext:
    return LearningContext(
        learner_id=learner.learner_id,
        context_type=ContextType.SCHOOL,
        program_code="school_11",
    )


def make_plan(
    learner: Learner,
    context: LearningContext,
    **overrides: object,
) -> StudyPlan:
    values = {
        "learner_id": learner.learner_id,
        "context_id": context.context_id,
        "title": "Haftalık plan",
        "plan_type": PlanType.WEEKLY,
        "start_date": MONDAY,
        "end_date": MONDAY + timedelta(days=1),
        "status": PlanStatus.DRAFT,
    }
    values.update(overrides)
    return StudyPlan(**values)


def make_task(
    plan: StudyPlan,
    context: LearningContext,
    minutes: int = 30,
    **overrides: object,
) -> StudyTask:
    values = {
        "plan_id": plan.plan_id,
        "context_id": context.context_id,
        "task_date": MONDAY,
        "task_type": TaskType.STUDY,
        "description": "Matematik",
        "planned_minutes": minutes,
    }
    values.update(overrides)
    return StudyTask(**values)


def make_availability(
    learner: Learner,
    minutes: int,
    day: DayOfWeek = DayOfWeek.MONDAY,
) -> Availability:
    return Availability(
        learner_id=learner.learner_id,
        day_of_week=day,
        availability_type=AvailabilityType.AVAILABLE,
        available_minutes=minutes,
    )


def make_snapshot(
    learner: Learner,
    contexts: tuple[LearningContext, ...],
    *,
    availability: tuple[Availability, ...] = (),
    goals: tuple[Goal, ...] = (),
    plans: tuple[StudyPlan, ...] = (),
    tasks: tuple[StudyTask, ...] = (),
) -> LearnerMemorySnapshot:
    return LearnerMemorySnapshot(
        learner=learner,
        contexts=contexts,
        goals=goals,
        availability=availability,
        assessments=(),
        assessment_results=(),
        learning_evidence=(),
        study_plans=plans,
        study_tasks=tasks,
        study_sessions=(),
        preferences=(),
        coaching_states=(),
    )


def valid_case() -> tuple[LearnerMemorySnapshot, StudyPlanWriteProposal]:
    learner = Learner()
    context = make_context(learner)
    plan = make_plan(learner, context)
    task = make_task(plan, context)
    snapshot = make_snapshot(
        learner,
        (context,),
        availability=(make_availability(learner, 60),),
    )
    return snapshot, StudyPlanWriteProposal(plan, (task,))


def test_valid_proposal_is_valid() -> None:
    snapshot, proposal = valid_case()

    report = validate_study_plan_write(snapshot, proposal)

    assert report.status == WriteValidationStatus.VALID
    assert report.violations == ()


def test_valid_proposal_reaches_persistence_boundary() -> None:
    snapshot, proposal = valid_case()
    memory = Mock(spec=LearnerMemoryService)
    memory.get_learner_memory_snapshot.return_value = snapshot

    report = write_study_plan_if_valid(
        memory,
        snapshot.learner.learner_id,
        proposal,
    )

    assert report.status == WriteValidationStatus.VALID
    memory.get_learner_memory_snapshot.assert_called_once_with(
        snapshot.learner.learner_id
    )
    memory.save_study_plan.assert_called_once_with(proposal.plan, proposal.tasks)


def test_exceeded_daily_availability_is_rejected_with_original_violation() -> None:
    snapshot, proposal = valid_case()
    proposal.tasks[0].planned_minutes = 61

    report = validate_study_plan_write(snapshot, proposal)

    assert report.status == WriteValidationStatus.REJECTED
    assert [item.rule_id for item in report.violations] == [
        "PLAN_AVAILABLE_TIME_LIMIT"
    ]
    assert "Planned 61 minutes exceeds the available 60 minutes" in (
        report.violations[0].message
    )


def test_unknown_availability_is_inconclusive() -> None:
    snapshot, proposal = valid_case()
    snapshot = make_snapshot(snapshot.learner, snapshot.contexts)

    report = validate_study_plan_write(snapshot, proposal)

    assert report.status == WriteValidationStatus.INCONCLUSIVE
    assert report.violations == ()


def test_ambiguous_availability_is_inconclusive() -> None:
    snapshot, proposal = valid_case()
    learner = snapshot.learner
    snapshot = make_snapshot(
        learner,
        snapshot.contexts,
        availability=(
            make_availability(learner, 60),
            make_availability(learner, 90),
        ),
    )

    assert validate_study_plan_write(snapshot, proposal).status == (
        WriteValidationStatus.INCONCLUSIVE
    )


@pytest.mark.parametrize(
    "snapshot_transform, expected",
    [
        (
            lambda snapshot: make_snapshot(snapshot.learner, snapshot.contexts),
            WriteValidationStatus.INCONCLUSIVE,
        ),
        (
            lambda snapshot: snapshot,
            WriteValidationStatus.REJECTED,
        ),
    ],
)
def test_non_valid_proposal_never_reaches_persistence(
    snapshot_transform: object,
    expected: WriteValidationStatus,
) -> None:
    snapshot, proposal = valid_case()
    snapshot = snapshot_transform(snapshot)
    if expected == WriteValidationStatus.REJECTED:
        proposal.tasks[0].planned_minutes = 61
    memory = Mock(spec=LearnerMemoryService)
    memory.get_learner_memory_snapshot.return_value = snapshot

    report = write_study_plan_if_valid(
        memory,
        snapshot.learner.learner_id,
        proposal,
    )

    assert report.status == expected
    memory.save_study_plan.assert_not_called()


def test_gateway_validates_the_fresh_snapshot_loaded_by_memory() -> None:
    stale_snapshot, proposal = valid_case()
    fresh_snapshot = make_snapshot(
        stale_snapshot.learner,
        stale_snapshot.contexts,
        availability=(make_availability(stale_snapshot.learner, 20),),
    )
    memory = Mock(spec=LearnerMemoryService)
    memory.get_learner_memory_snapshot.return_value = fresh_snapshot

    report = write_study_plan_if_valid(
        memory,
        stale_snapshot.learner.learner_id,
        proposal,
    )

    assert report.status == WriteValidationStatus.REJECTED
    assert report.violations[0].rule_id == "PLAN_AVAILABLE_TIME_LIMIT"
    memory.get_learner_memory_snapshot.assert_called_once_with(
        stale_snapshot.learner.learner_id
    )
    memory.save_study_plan.assert_not_called()


def test_gateway_rejects_proposal_for_another_active_learner() -> None:
    snapshot, proposal = valid_case()
    proposal.plan.learner_id = uuid4()
    memory = Mock(spec=LearnerMemoryService)
    memory.get_learner_memory_snapshot.return_value = snapshot

    report = write_study_plan_if_valid(
        memory,
        snapshot.learner.learner_id,
        proposal,
    )

    assert report.status == WriteValidationStatus.REJECTED
    assert report.violations[0].rule_id == "STUDY_PLAN_LEARNER_OWNERSHIP"
    memory.save_study_plan.assert_not_called()


def test_plan_for_another_learner_is_rejected() -> None:
    snapshot, proposal = valid_case()
    proposal.plan.learner_id = uuid4()

    report = validate_study_plan_write(snapshot, proposal)

    assert report.status == WriteValidationStatus.REJECTED
    assert report.violations[0].rule_id == "STUDY_PLAN_LEARNER_OWNERSHIP"


def test_context_not_owned_by_snapshot_learner_is_rejected() -> None:
    snapshot, proposal = valid_case()
    foreign_context = make_context(Learner())
    proposal.plan.context_id = foreign_context.context_id
    proposal.tasks[0].context_id = foreign_context.context_id

    report = validate_study_plan_write(snapshot, proposal)

    assert report.status == WriteValidationStatus.REJECTED
    assert {item.rule_id for item in report.violations} >= {
        "STUDY_PLAN_CONTEXT_OWNERSHIP",
        "STUDY_TASK_CONTEXT_OWNERSHIP",
    }


def test_task_for_another_plan_is_rejected() -> None:
    snapshot, proposal = valid_case()
    proposal.tasks[0].plan_id = uuid4()

    report = validate_study_plan_write(snapshot, proposal)

    assert "STUDY_TASK_PLAN_RELATIONSHIP" in {
        item.rule_id for item in report.violations
    }


def test_task_outside_plan_date_range_is_rejected() -> None:
    snapshot, proposal = valid_case()
    proposal.tasks[0].task_date = proposal.plan.end_date + timedelta(days=1)

    report = validate_study_plan_write(snapshot, proposal)

    assert "STUDY_TASK_DATE_RANGE" in {item.rule_id for item in report.violations}


def test_context_specific_plan_rejects_task_from_another_context() -> None:
    snapshot, proposal = valid_case()
    second_context = make_context(snapshot.learner)
    snapshot = make_snapshot(
        snapshot.learner,
        snapshot.contexts + (second_context,),
        availability=snapshot.availability,
    )
    proposal.tasks[0].context_id = second_context.context_id

    report = validate_study_plan_write(snapshot, proposal)

    assert "STUDY_TASK_CONTEXT_CONSISTENCY" in {
        item.rule_id for item in report.violations
    }


def test_context_specific_plan_rejects_goal_from_another_context() -> None:
    snapshot, proposal = valid_case()
    second_context = make_context(snapshot.learner)
    goal = Goal(
        learner_id=snapshot.learner.learner_id,
        context_id=second_context.context_id,
        goal_type="exam_target",
        description="Hedef",
    )
    proposal.plan.goal_id = goal.goal_id
    snapshot = make_snapshot(
        snapshot.learner,
        snapshot.contexts + (second_context,),
        availability=snapshot.availability,
        goals=(goal,),
    )

    report = validate_study_plan_write(snapshot, proposal)

    assert "STUDY_PLAN_GOAL_CONTEXT_CONSISTENCY" in {
        item.rule_id for item in report.violations
    }


def test_persisted_and_candidate_plans_share_daily_budget() -> None:
    snapshot, proposal = valid_case()
    context = snapshot.contexts[0]
    persisted = make_plan(
        snapshot.learner,
        context,
        status=PlanStatus.ACTIVE,
    )
    persisted_task = make_task(persisted, context, 40)
    snapshot = make_snapshot(
        snapshot.learner,
        snapshot.contexts,
        availability=(make_availability(snapshot.learner, 60),),
        plans=(persisted,),
        tasks=(persisted_task,),
    )

    report = validate_study_plan_write(snapshot, proposal)

    assert report.status == WriteValidationStatus.REJECTED
    assert report.violations[0].rule_id == "PLAN_AVAILABLE_TIME_LIMIT"


def test_candidate_replacement_does_not_double_count_persisted_plan() -> None:
    snapshot, proposal = valid_case()
    context = snapshot.contexts[0]
    persisted = proposal.plan.model_copy(update={"status": PlanStatus.ACTIVE})
    old_task = make_task(persisted, context, 60)
    snapshot = make_snapshot(
        snapshot.learner,
        snapshot.contexts,
        availability=(make_availability(snapshot.learner, 60),),
        plans=(persisted,),
        tasks=(old_task,),
    )

    report = validate_study_plan_write(snapshot, proposal)

    assert report.status == WriteValidationStatus.VALID


def test_multi_day_plan_evaluates_every_task_date() -> None:
    snapshot, proposal = valid_case()
    context = snapshot.contexts[0]
    tuesday = make_task(
        proposal.plan,
        context,
        61,
        task_date=MONDAY + timedelta(days=1),
    )
    proposal = StudyPlanWriteProposal(proposal.plan, proposal.tasks + (tuesday,))
    snapshot = make_snapshot(
        snapshot.learner,
        snapshot.contexts,
        availability=(
            make_availability(snapshot.learner, 60),
            make_availability(snapshot.learner, 60, DayOfWeek.TUESDAY),
        ),
    )

    report = validate_study_plan_write(snapshot, proposal)

    assert report.status == WriteValidationStatus.REJECTED
    assert "2026-10-06" in report.violations[0].message


def test_valid_day_and_unknown_day_are_inconclusive() -> None:
    snapshot, proposal = valid_case()
    context = snapshot.contexts[0]
    tuesday = make_task(
        proposal.plan,
        context,
        task_date=MONDAY + timedelta(days=1),
    )
    proposal = StudyPlanWriteProposal(proposal.plan, proposal.tasks + (tuesday,))

    assert validate_study_plan_write(snapshot, proposal).status == (
        WriteValidationStatus.INCONCLUSIVE
    )


def test_unknown_day_and_budget_violation_are_rejected() -> None:
    snapshot, proposal = valid_case()
    context = snapshot.contexts[0]
    proposal.tasks[0].planned_minutes = 61
    tuesday = make_task(
        proposal.plan,
        context,
        task_date=MONDAY + timedelta(days=1),
    )
    proposal = StudyPlanWriteProposal(proposal.plan, proposal.tasks + (tuesday,))

    report = validate_study_plan_write(snapshot, proposal)

    assert report.status == WriteValidationStatus.REJECTED
    assert report.violations[0].rule_id == "PLAN_AVAILABLE_TIME_LIMIT"


def test_validation_is_pure_and_repeatable_without_a_repository() -> None:
    snapshot, proposal = valid_case()

    assert validate_study_plan_write(snapshot, proposal) == (
        validate_study_plan_write(snapshot, proposal)
    )


def test_task_input_order_does_not_change_validation_report() -> None:
    snapshot, proposal = valid_case()
    context = snapshot.contexts[0]
    second = make_task(proposal.plan, context, 10)
    forward = StudyPlanWriteProposal(proposal.plan, proposal.tasks + (second,))
    reverse = StudyPlanWriteProposal(proposal.plan, tuple(reversed(forward.tasks)))

    assert validate_study_plan_write(snapshot, forward) == (
        validate_study_plan_write(snapshot, reverse)
    )


def test_contracts_are_immutable() -> None:
    snapshot, proposal = valid_case()
    report = validate_study_plan_write(snapshot, proposal)

    with pytest.raises(FrozenInstanceError):
        proposal.tasks = ()
    with pytest.raises(FrozenInstanceError):
        report.status = WriteValidationStatus.REJECTED
