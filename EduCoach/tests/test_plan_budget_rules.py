from dataclasses import FrozenInstanceError
from datetime import date, datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest

from educoach.models import (
    Availability,
    AvailabilityType,
    DayOfWeek,
    Learner,
    PlanStatus,
    PlanType,
    StudyPlan,
    StudySession,
    StudyTask,
    TaskStatus,
    TaskType,
)
from educoach.rules import (
    DailyPlannedLoadProjection,
    PlanAvailableTimeLimitResult,
    RuleEvaluation,
    RuleSeverity,
    TimeBudgetResolutionStatus,
    evaluate_plan_available_time_limit,
    project_daily_planned_load,
    resolve_daily_time_budget,
)
from educoach.services.snapshot import LearnerMemorySnapshot


TARGET_DATE = date(2026, 10, 5)


def make_plan(
    learner: Learner,
    *,
    status: PlanStatus = PlanStatus.ACTIVE,
    context_id: UUID | None = None,
    plan_id: UUID | None = None,
    start_date: date = TARGET_DATE,
    end_date: date = TARGET_DATE,
) -> StudyPlan:
    values = {
        "learner_id": learner.learner_id,
        "context_id": context_id,
        "title": "Plan",
        "plan_type": PlanType.DAILY,
        "start_date": start_date,
        "end_date": end_date,
        "status": status,
    }
    if plan_id is not None:
        values["plan_id"] = plan_id
    return StudyPlan(**values)


def make_task(
    plan: StudyPlan,
    minutes: int,
    *,
    status: TaskStatus = TaskStatus.PENDING,
    context_id: UUID | None = None,
    task_id: UUID | None = None,
    task_date: date = TARGET_DATE,
) -> StudyTask:
    values = {
        "plan_id": plan.plan_id,
        "context_id": context_id or plan.context_id or uuid4(),
        "task_date": task_date,
        "task_type": TaskType.STUDY,
        "description": "Task",
        "planned_minutes": minutes,
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


def make_availability(minutes: int) -> Availability:
    return Availability(
        learner_id=uuid4(),
        day_of_week=DayOfWeek.MONDAY,
        availability_type=AvailabilityType.AVAILABLE,
        available_minutes=minutes,
    )


def make_snapshot(
    learner: Learner,
    *,
    plans: tuple[StudyPlan, ...] = (),
    tasks: tuple[StudyTask, ...] = (),
    availability: tuple[Availability, ...] = (),
    sessions: tuple[StudySession, ...] = (),
) -> LearnerMemorySnapshot:
    return LearnerMemorySnapshot(
        learner=learner,
        contexts=(),
        goals=(),
        availability=availability,
        assessments=(),
        assessment_results=(),
        learning_evidence=(),
        study_plans=plans,
        study_tasks=tasks,
        study_sessions=sessions,
        preferences=(),
        coaching_states=(),
    )


def test_single_persisted_active_plan_is_projected() -> None:
    learner = Learner()
    plan = make_plan(learner)
    task = make_task(plan, 45)

    projection = project_daily_planned_load(
        make_snapshot(learner, plans=(plan,), tasks=(task,)),
        TARGET_DATE,
    )

    assert projection.planned_minutes == 45
    assert projection.included_task_ids == (task.task_id,)


def test_two_persisted_active_plans_are_aggregated() -> None:
    learner = Learner()
    first_plan = make_plan(learner)
    second_plan = make_plan(learner)
    first_task = make_task(first_plan, 40)
    second_task = make_task(second_plan, 50)

    projection = project_daily_planned_load(
        make_snapshot(
            learner,
            plans=(first_plan, second_plan),
            tasks=(first_task, second_task),
        ),
        TARGET_DATE,
    )

    assert projection.planned_minutes == 90


def test_different_contexts_share_the_learner_budget() -> None:
    learner = Learner()
    first_plan = make_plan(learner, context_id=uuid4())
    second_plan = make_plan(learner, context_id=uuid4())
    first_task = make_task(first_plan, 70)
    second_task = make_task(second_plan, 80)
    snapshot = make_snapshot(
        learner,
        plans=(first_plan, second_plan),
        tasks=(first_task, second_task),
        availability=(make_availability(120),),
    )

    result = evaluate_plan_available_time_limit(snapshot, TARGET_DATE)

    assert result.planned_load.planned_minutes == 150
    assert len(result.evaluation.violations) == 1


def test_task_for_another_date_is_excluded() -> None:
    learner = Learner()
    plan = make_plan(learner, end_date=TARGET_DATE + timedelta(days=1))
    today = make_task(plan, 30)
    tomorrow = make_task(plan, 90, task_date=TARGET_DATE + timedelta(days=1))

    projection = project_daily_planned_load(
        make_snapshot(learner, plans=(plan,), tasks=(tomorrow, today)),
        TARGET_DATE,
    )

    assert projection.planned_minutes == 30
    assert projection.included_task_ids == (today.task_id,)


@pytest.mark.parametrize(
    ("status", "included"),
    [
        (PlanStatus.DRAFT, False),
        (PlanStatus.ACTIVE, True),
        (PlanStatus.COMPLETED, True),
        (PlanStatus.CANCELLED, False),
    ],
)
def test_persisted_plan_status_policy(status: PlanStatus, included: bool) -> None:
    learner = Learner()
    plan = make_plan(learner, status=status)
    task = make_task(plan, 30)

    projection = project_daily_planned_load(
        make_snapshot(learner, plans=(plan,), tasks=(task,)),
        TARGET_DATE,
    )

    assert projection.planned_minutes == (30 if included else 0)


@pytest.mark.parametrize(
    ("status", "included"),
    [
        (PlanStatus.DRAFT, True),
        (PlanStatus.ACTIVE, True),
        (PlanStatus.COMPLETED, True),
        (PlanStatus.CANCELLED, False),
    ],
)
def test_candidate_plan_status_policy(status: PlanStatus, included: bool) -> None:
    learner = Learner()
    candidate = make_plan(learner, status=status)
    task = make_task(candidate, 30)

    projection = project_daily_planned_load(
        make_snapshot(learner),
        TARGET_DATE,
        candidate_plan=candidate,
        candidate_tasks=(task,),
    )

    assert projection.planned_minutes == (30 if included else 0)


@pytest.mark.parametrize(
    ("status", "included"),
    [
        (TaskStatus.PENDING, True),
        (TaskStatus.IN_PROGRESS, True),
        (TaskStatus.COMPLETED, True),
        (TaskStatus.SKIPPED, False),
        (TaskStatus.CANCELLED, False),
    ],
)
def test_task_status_policy(status: TaskStatus, included: bool) -> None:
    learner = Learner()
    plan = make_plan(learner)
    task = make_task(plan, 35, status=status)

    projection = project_daily_planned_load(
        make_snapshot(learner, plans=(plan,), tasks=(task,)),
        TARGET_DATE,
    )

    assert projection.planned_minutes == (35 if included else 0)


def test_exact_budget_boundary_has_no_violation() -> None:
    learner = Learner()
    plan = make_plan(learner)
    task = make_task(plan, 60)
    snapshot = make_snapshot(
        learner,
        plans=(plan,),
        tasks=(task,),
        availability=(make_availability(60),),
    )

    result = evaluate_plan_available_time_limit(snapshot, TARGET_DATE)

    assert result.budget.status == TimeBudgetResolutionStatus.RESOLVED
    assert result.evaluation == RuleEvaluation()


def test_budget_exceed_creates_one_deterministic_error() -> None:
    learner = Learner()
    plan = make_plan(learner)
    task = make_task(plan, 61)
    snapshot = make_snapshot(
        learner,
        plans=(plan,),
        tasks=(task,),
        availability=(make_availability(60),),
    )

    result = evaluate_plan_available_time_limit(snapshot, TARGET_DATE)

    assert len(result.evaluation.violations) == 1
    violation = result.evaluation.violations[0]
    assert violation.rule_id == "PLAN_AVAILABLE_TIME_LIMIT"
    assert violation.severity == RuleSeverity.ERROR
    assert violation.message == (
        "Planned 61 minutes exceeds the available 60 minutes for 2026-10-05."
    )


def test_unknown_budget_preserves_status_without_violation() -> None:
    learner = Learner()
    result = evaluate_plan_available_time_limit(
        make_snapshot(learner),
        TARGET_DATE,
    )

    assert result.budget.status == TimeBudgetResolutionStatus.UNKNOWN
    assert result.planned_load.planned_minutes == 0
    assert result.evaluation.violations == ()


def test_ambiguous_budget_preserves_status_without_violation() -> None:
    learner = Learner()
    snapshot = make_snapshot(
        learner,
        availability=(make_availability(60), make_availability(90)),
    )

    result = evaluate_plan_available_time_limit(snapshot, TARGET_DATE)

    assert result.budget.status == TimeBudgetResolutionStatus.AMBIGUOUS
    assert result.planned_load.planned_minutes == 0
    assert result.evaluation.violations == ()


def test_persisted_and_new_candidate_loads_are_added() -> None:
    learner = Learner()
    persisted_plan = make_plan(learner)
    persisted_task = make_task(persisted_plan, 60)
    candidate_plan = make_plan(learner, status=PlanStatus.DRAFT)
    candidate_task = make_task(candidate_plan, 90)
    snapshot = make_snapshot(
        learner,
        plans=(persisted_plan,),
        tasks=(persisted_task,),
        availability=(make_availability(120),),
    )

    result = evaluate_plan_available_time_limit(
        snapshot,
        TARGET_DATE,
        candidate_plan=candidate_plan,
        candidate_tasks=(candidate_task,),
    )

    assert result.planned_load.planned_minutes == 150
    assert result.evaluation.violations[0].rule_id == "PLAN_AVAILABLE_TIME_LIMIT"


def test_existing_candidate_plan_completely_replaces_persisted_tasks() -> None:
    learner = Learner()
    plan_id = uuid4()
    persisted_plan = make_plan(learner, plan_id=plan_id)
    old_first = make_task(persisted_plan, 50)
    old_second = make_task(persisted_plan, 70)
    candidate_plan = make_plan(
        learner,
        status=PlanStatus.DRAFT,
        plan_id=plan_id,
    )
    replacement = make_task(candidate_plan, 40, task_id=old_first.task_id)
    snapshot = make_snapshot(
        learner,
        plans=(persisted_plan,),
        tasks=(old_first, old_second),
    )

    projection = project_daily_planned_load(
        snapshot,
        TARGET_DATE,
        candidate_plan=candidate_plan,
        candidate_tasks=(replacement,),
    )

    assert projection.planned_minutes == 40
    assert projection.included_task_ids == (replacement.task_id,)


@pytest.mark.parametrize(
    ("persisted_date", "persisted_status"),
    [
        (TARGET_DATE + timedelta(days=1), TaskStatus.PENDING),
        (TARGET_DATE, TaskStatus.SKIPPED),
    ],
)
def test_candidate_task_id_from_another_persisted_plan_is_rejected(
    persisted_date: date,
    persisted_status: TaskStatus,
) -> None:
    learner = Learner()
    persisted_plan = make_plan(
        learner,
        end_date=TARGET_DATE + timedelta(days=1),
    )
    shared_task_id = uuid4()
    persisted_task = make_task(
        persisted_plan,
        30,
        task_id=shared_task_id,
        task_date=persisted_date,
        status=persisted_status,
    )
    candidate_plan = make_plan(learner, status=PlanStatus.DRAFT)
    candidate_task = make_task(
        candidate_plan,
        45,
        task_id=shared_task_id,
    )

    with pytest.raises(ValueError, match="another persisted plan"):
        project_daily_planned_load(
            make_snapshot(
                learner,
                plans=(persisted_plan,),
                tasks=(persisted_task,),
            ),
            TARGET_DATE,
            candidate_plan=candidate_plan,
            candidate_tasks=(candidate_task,),
        )


def test_duplicate_candidate_task_id_is_rejected() -> None:
    learner = Learner()
    candidate = make_plan(learner)
    task_id = uuid4()

    with pytest.raises(ValueError, match="duplicate task_id"):
        project_daily_planned_load(
            make_snapshot(learner),
            TARGET_DATE,
            candidate_plan=candidate,
            candidate_tasks=(
                make_task(candidate, 20, task_id=task_id),
                make_task(candidate, 30, task_id=task_id),
            ),
        )


def test_candidate_task_for_another_plan_is_rejected() -> None:
    learner = Learner()
    candidate = make_plan(learner)
    other = make_plan(learner)

    with pytest.raises(ValueError, match="belong to the candidate plan"):
        project_daily_planned_load(
            make_snapshot(learner),
            TARGET_DATE,
            candidate_plan=candidate,
            candidate_tasks=(make_task(other, 30),),
        )


def test_candidate_task_outside_plan_dates_is_rejected() -> None:
    learner = Learner()
    candidate = make_plan(learner)

    with pytest.raises(ValueError, match="date"):
        project_daily_planned_load(
            make_snapshot(learner),
            TARGET_DATE,
            candidate_plan=candidate,
            candidate_tasks=(
                make_task(candidate, 30, task_date=TARGET_DATE + timedelta(days=1)),
            ),
        )


def test_context_specific_candidate_rejects_another_context() -> None:
    learner = Learner()
    candidate = make_plan(learner, context_id=uuid4())

    with pytest.raises(ValueError, match="context"):
        project_daily_planned_load(
            make_snapshot(learner),
            TARGET_DATE,
            candidate_plan=candidate,
            candidate_tasks=(make_task(candidate, 30, context_id=uuid4()),),
        )


def test_candidate_plan_for_another_learner_is_rejected() -> None:
    learner = Learner()
    candidate = make_plan(Learner())

    with pytest.raises(ValueError, match="snapshot learner"):
        project_daily_planned_load(
            make_snapshot(learner),
            TARGET_DATE,
            candidate_plan=candidate,
        )


def test_candidate_tasks_without_candidate_plan_are_rejected() -> None:
    learner = Learner()
    plan = make_plan(learner)

    with pytest.raises(ValueError, match="require a candidate_plan"):
        project_daily_planned_load(
            make_snapshot(learner),
            TARGET_DATE,
            candidate_tasks=(make_task(plan, 30),),
        )


def test_persisted_orphan_task_is_rejected() -> None:
    learner = Learner()
    orphan_plan = make_plan(learner)

    with pytest.raises(ValueError, match="snapshot plan"):
        project_daily_planned_load(
            make_snapshot(learner, tasks=(make_task(orphan_plan, 30),)),
            TARGET_DATE,
        )


def test_duplicate_persisted_plan_id_is_rejected() -> None:
    learner = Learner()
    plan_id = uuid4()

    with pytest.raises(ValueError, match="duplicate plan_id"):
        project_daily_planned_load(
            make_snapshot(
                learner,
                plans=(
                    make_plan(learner, plan_id=plan_id),
                    make_plan(learner, plan_id=plan_id),
                ),
            ),
            TARGET_DATE,
        )


def test_duplicate_persisted_task_id_is_rejected() -> None:
    learner = Learner()
    plan = make_plan(learner)
    task_id = uuid4()

    with pytest.raises(ValueError, match="duplicate task_id"):
        project_daily_planned_load(
            make_snapshot(
                learner,
                plans=(plan,),
                tasks=(
                    make_task(plan, 20, task_id=task_id),
                    make_task(plan, 30, task_id=task_id),
                ),
            ),
            TARGET_DATE,
        )


def test_persisted_plan_for_another_learner_is_rejected() -> None:
    learner = Learner()
    other_plan = make_plan(Learner())

    with pytest.raises(ValueError, match="snapshot learner"):
        project_daily_planned_load(
            make_snapshot(learner, plans=(other_plan,)),
            TARGET_DATE,
        )


def test_actual_session_duration_does_not_affect_projection() -> None:
    learner = Learner()
    context_id = uuid4()
    plan = make_plan(learner, context_id=context_id)
    task = make_task(plan, 60)
    session = StudySession(
        learner_id=learner.learner_id,
        context_id=context_id,
        task_id=task.task_id,
        duration_minutes=15,
    )

    projection = project_daily_planned_load(
        make_snapshot(
            learner,
            plans=(plan,),
            tasks=(task,),
            sessions=(session,),
        ),
        TARGET_DATE,
    )

    assert projection.planned_minutes == 60


def test_projection_is_immutable() -> None:
    projection = DailyPlannedLoadProjection(TARGET_DATE, 0, ())

    with pytest.raises(FrozenInstanceError):
        projection.planned_minutes = 10


def test_composite_result_is_immutable() -> None:
    learner = Learner()
    result = evaluate_plan_available_time_limit(make_snapshot(learner), TARGET_DATE)

    with pytest.raises(FrozenInstanceError):
        result.evaluation = RuleEvaluation()


@pytest.mark.parametrize("minutes", [True, -1])
def test_projection_rejects_invalid_planned_minutes(minutes: int) -> None:
    with pytest.raises(ValueError, match="planned_minutes"):
        DailyPlannedLoadProjection(TARGET_DATE, minutes, ())


def test_projection_requires_tuple_task_ids() -> None:
    with pytest.raises(ValueError, match="tuple"):
        DailyPlannedLoadProjection(TARGET_DATE, 0, [])


def test_projection_rejects_duplicate_task_ids() -> None:
    task_id = uuid4()

    with pytest.raises(ValueError, match="duplicates"):
        DailyPlannedLoadProjection(TARGET_DATE, 1, (task_id, task_id))


def test_included_task_ids_are_deterministic_and_unique() -> None:
    learner = Learner()
    plan = make_plan(learner)
    later_id = UUID(int=2)
    earlier_id = UUID(int=1)
    later = make_task(plan, 20, task_id=later_id)
    earlier = make_task(plan, 10, task_id=earlier_id)

    projection = project_daily_planned_load(
        make_snapshot(learner, plans=(plan,), tasks=(later, earlier)),
        TARGET_DATE,
    )

    assert projection.included_task_ids == (earlier_id, later_id)
    assert projection.planned_minutes == 30


def test_composite_result_rejects_mismatched_dates() -> None:
    budget = resolve_daily_time_budget((), TARGET_DATE)
    load = DailyPlannedLoadProjection(TARGET_DATE + timedelta(days=1), 0, ())

    with pytest.raises(ValueError, match="target dates"):
        PlanAvailableTimeLimitResult(budget, load, RuleEvaluation())
