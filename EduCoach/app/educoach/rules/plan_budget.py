"""Pure learner-level planned-load projection and daily budget validation."""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from educoach.models import PlanStatus, StudyPlan, StudyTask, TaskStatus
from educoach.services.snapshot import LearnerMemorySnapshot

from .availability import (
    DailyTimeBudgetResolution,
    TimeBudgetResolutionStatus,
    resolve_daily_time_budget,
)
from .contracts import RuleEvaluation, RuleSeverity, RuleViolation


_PERSISTED_INCLUDED_PLAN_STATUSES = frozenset(
    {PlanStatus.ACTIVE, PlanStatus.COMPLETED}
)
_CANDIDATE_INCLUDED_PLAN_STATUSES = frozenset(
    {PlanStatus.DRAFT, PlanStatus.ACTIVE, PlanStatus.COMPLETED}
)
_INCLUDED_TASK_STATUSES = frozenset(
    {TaskStatus.PENDING, TaskStatus.IN_PROGRESS, TaskStatus.COMPLETED}
)


@dataclass(frozen=True)
class DailyPlannedLoadProjection:
    target_date: date
    planned_minutes: int
    included_task_ids: tuple[UUID, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.target_date, date) or isinstance(
            self.target_date, datetime
        ):
            raise ValueError("target_date must be a date")
        if (
            isinstance(self.planned_minutes, bool)
            or not isinstance(self.planned_minutes, int)
            or self.planned_minutes < 0
        ):
            raise ValueError("planned_minutes must be a non-negative integer")
        if not isinstance(self.included_task_ids, tuple):
            raise ValueError("included_task_ids must be a tuple")
        if len(set(self.included_task_ids)) != len(self.included_task_ids):
            raise ValueError("included_task_ids cannot contain duplicates")


@dataclass(frozen=True)
class PlanAvailableTimeLimitResult:
    budget: DailyTimeBudgetResolution
    planned_load: DailyPlannedLoadProjection
    evaluation: RuleEvaluation

    def __post_init__(self) -> None:
        if not isinstance(self.budget, DailyTimeBudgetResolution):
            raise ValueError("budget must be a DailyTimeBudgetResolution")
        if not isinstance(self.planned_load, DailyPlannedLoadProjection):
            raise ValueError("planned_load must be a DailyPlannedLoadProjection")
        if not isinstance(self.evaluation, RuleEvaluation):
            raise ValueError("evaluation must be a RuleEvaluation")
        if self.budget.target_date != self.planned_load.target_date:
            raise ValueError("budget and planned_load target dates must match")


def project_daily_planned_load(
    snapshot: LearnerMemorySnapshot,
    target_date: date,
    *,
    candidate_plan: StudyPlan | None = None,
    candidate_tasks: Iterable[StudyTask] = (),
) -> DailyPlannedLoadProjection:
    """Project one learner's eligible planned minutes for an explicit date."""

    candidate_task_items = tuple(candidate_tasks)
    persisted_plans = _index_persisted_plans(snapshot)
    persisted_tasks = _index_persisted_tasks(snapshot, persisted_plans)
    _validate_candidate(
        snapshot,
        candidate_plan,
        candidate_task_items,
        persisted_tasks,
    )

    replaced_plan_id = candidate_plan.plan_id if candidate_plan is not None else None
    included_tasks = [
        task
        for task in persisted_tasks.values()
        if task.plan_id != replaced_plan_id
        and persisted_plans[task.plan_id].status
        in _PERSISTED_INCLUDED_PLAN_STATUSES
        and task.status in _INCLUDED_TASK_STATUSES
        and task.task_date == target_date
    ]

    if (
        candidate_plan is not None
        and candidate_plan.status in _CANDIDATE_INCLUDED_PLAN_STATUSES
    ):
        included_tasks.extend(
            task
            for task in candidate_task_items
            if task.status in _INCLUDED_TASK_STATUSES
            and task.task_date == target_date
        )

    included_tasks.sort(key=lambda task: str(task.task_id))
    return DailyPlannedLoadProjection(
        target_date=target_date,
        planned_minutes=sum(task.planned_minutes for task in included_tasks),
        included_task_ids=tuple(task.task_id for task in included_tasks),
    )


def evaluate_plan_available_time_limit(
    snapshot: LearnerMemorySnapshot,
    target_date: date,
    *,
    candidate_plan: StudyPlan | None = None,
    candidate_tasks: Iterable[StudyTask] = (),
) -> PlanAvailableTimeLimitResult:
    """Evaluate PLAN_AVAILABLE_TIME_LIMIT without hiding budget resolution."""

    planned_load = project_daily_planned_load(
        snapshot,
        target_date,
        candidate_plan=candidate_plan,
        candidate_tasks=candidate_tasks,
    )
    budget = resolve_daily_time_budget(snapshot.availability, target_date)
    violations: tuple[RuleViolation, ...] = ()

    if budget.status == TimeBudgetResolutionStatus.RESOLVED:
        assert budget.available_minutes is not None
        if planned_load.planned_minutes > budget.available_minutes:
            violations = (
                RuleViolation(
                    rule_id="PLAN_AVAILABLE_TIME_LIMIT",
                    severity=RuleSeverity.ERROR,
                    message=(
                        f"Planned {planned_load.planned_minutes} minutes exceeds "
                        f"the available {budget.available_minutes} minutes for "
                        f"{target_date.isoformat()}."
                    ),
                ),
            )

    return PlanAvailableTimeLimitResult(
        budget=budget,
        planned_load=planned_load,
        evaluation=RuleEvaluation(violations=violations),
    )


def _index_persisted_plans(
    snapshot: LearnerMemorySnapshot,
) -> dict[UUID, StudyPlan]:
    plans: dict[UUID, StudyPlan] = {}
    learner_id = snapshot.learner.learner_id

    for plan in snapshot.study_plans:
        if plan.plan_id in plans:
            raise ValueError("snapshot cannot contain duplicate plan_id values")
        if plan.learner_id != learner_id:
            raise ValueError("persisted plan must belong to the snapshot learner")
        plans[plan.plan_id] = plan

    return plans


def _index_persisted_tasks(
    snapshot: LearnerMemorySnapshot,
    persisted_plans: dict[UUID, StudyPlan],
) -> dict[UUID, StudyTask]:
    tasks: dict[UUID, StudyTask] = {}

    for task in snapshot.study_tasks:
        if task.task_id in tasks:
            raise ValueError("snapshot cannot contain duplicate task_id values")
        if task.plan_id not in persisted_plans:
            raise ValueError("persisted task must reference a snapshot plan")
        tasks[task.task_id] = task

    return tasks


def _validate_candidate(
    snapshot: LearnerMemorySnapshot,
    candidate_plan: StudyPlan | None,
    candidate_tasks: tuple[StudyTask, ...],
    persisted_tasks: dict[UUID, StudyTask],
) -> None:
    if candidate_plan is None:
        if candidate_tasks:
            raise ValueError("candidate_tasks require a candidate_plan")
        return

    if candidate_plan.learner_id != snapshot.learner.learner_id:
        raise ValueError("candidate plan must belong to the snapshot learner")

    task_ids: set[UUID] = set()
    for task in candidate_tasks:
        if task.task_id in task_ids:
            raise ValueError("candidate_tasks cannot contain duplicate task_id values")
        task_ids.add(task.task_id)

        persisted_task = persisted_tasks.get(task.task_id)
        if (
            persisted_task is not None
            and persisted_task.plan_id != candidate_plan.plan_id
        ):
            raise ValueError(
                "candidate task_id cannot belong to another persisted plan"
            )

        if task.plan_id != candidate_plan.plan_id:
            raise ValueError("candidate task must belong to the candidate plan")
        if not (
            candidate_plan.start_date
            <= task.task_date
            <= candidate_plan.end_date
        ):
            raise ValueError("candidate task date must be within the candidate plan")
        if (
            candidate_plan.context_id is not None
            and task.context_id != candidate_plan.context_id
        ):
            raise ValueError("candidate task must match the candidate plan context")
