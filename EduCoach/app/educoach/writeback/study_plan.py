"""Deterministic validation and persistence boundary for StudyPlan writes."""

from collections.abc import Iterable
from uuid import UUID

from educoach.rules.availability import TimeBudgetResolutionStatus
from educoach.rules.contracts import RuleSeverity, RuleViolation
from educoach.rules.plan_budget import evaluate_plan_available_time_limit
from educoach.services.learner_memory import LearnerMemoryService
from educoach.services.snapshot import LearnerMemorySnapshot

from .contracts import (
    StudyPlanWriteProposal,
    StudyPlanWriteValidationReport,
    WriteValidationStatus,
)


def validate_study_plan_write(
    snapshot: LearnerMemorySnapshot,
    proposal: StudyPlanWriteProposal,
) -> StudyPlanWriteValidationReport:
    """Validate a proposed plan write without I/O or hidden runtime state."""

    violations = _validate_relationships(snapshot, proposal)
    if violations:
        return StudyPlanWriteValidationReport(
            status=WriteValidationStatus.REJECTED,
            violations=violations,
        )

    budget_violations: list[RuleViolation] = []
    has_inconclusive_budget = False
    ordered_tasks = tuple(sorted(proposal.tasks, key=lambda task: str(task.task_id)))

    for target_date in sorted({task.task_date for task in ordered_tasks}):
        result = evaluate_plan_available_time_limit(
            snapshot,
            target_date,
            candidate_plan=proposal.plan,
            candidate_tasks=ordered_tasks,
        )
        budget_violations.extend(result.evaluation.violations)
        if result.budget.status in {
            TimeBudgetResolutionStatus.UNKNOWN,
            TimeBudgetResolutionStatus.AMBIGUOUS,
        }:
            has_inconclusive_budget = True

    if budget_violations:
        return StudyPlanWriteValidationReport(
            status=WriteValidationStatus.REJECTED,
            violations=_deduplicate(budget_violations),
        )
    if has_inconclusive_budget:
        return StudyPlanWriteValidationReport(
            status=WriteValidationStatus.INCONCLUSIVE,
        )
    return StudyPlanWriteValidationReport(status=WriteValidationStatus.VALID)


def write_study_plan_if_valid(
    memory: LearnerMemoryService,
    learner_id: UUID,
    proposal: StudyPlanWriteProposal,
) -> StudyPlanWriteValidationReport:
    """Persist a proposal through LearnerMemoryService only when it is valid."""

    snapshot = memory.get_learner_memory_snapshot(learner_id)
    report = validate_study_plan_write(snapshot, proposal)
    if report.status == WriteValidationStatus.VALID:
        memory.save_study_plan(proposal.plan, proposal.tasks)
    return report


def _validate_relationships(
    snapshot: LearnerMemorySnapshot,
    proposal: StudyPlanWriteProposal,
) -> tuple[RuleViolation, ...]:
    plan = proposal.plan
    learner_id = snapshot.learner.learner_id
    violations: list[RuleViolation] = []

    if plan.learner_id != learner_id:
        violations.append(_violation(
            "STUDY_PLAN_LEARNER_OWNERSHIP",
            "StudyPlan must belong to the snapshot learner.",
        ))

    learner_context_ids = {
        context.context_id
        for context in snapshot.contexts
        if context.learner_id == learner_id
    }
    if plan.context_id is not None and plan.context_id not in learner_context_ids:
        violations.append(_violation(
            "STUDY_PLAN_CONTEXT_OWNERSHIP",
            "StudyPlan context must belong to the snapshot learner.",
        ))

    goal = next(
        (item for item in snapshot.goals if item.goal_id == plan.goal_id),
        None,
    )
    if plan.goal_id is not None:
        if goal is None or goal.learner_id != learner_id:
            violations.append(_violation(
                "STUDY_PLAN_GOAL_OWNERSHIP",
                "StudyPlan goal must belong to the snapshot learner.",
            ))
        elif (
            plan.context_id is not None
            and goal.context_id is not None
            and goal.context_id != plan.context_id
        ):
            violations.append(_violation(
                "STUDY_PLAN_GOAL_CONTEXT_CONSISTENCY",
                "A context-specific StudyPlan cannot use a Goal from another context.",
            ))

    task_ids = [task.task_id for task in proposal.tasks]
    if len(set(task_ids)) != len(task_ids):
        violations.append(_violation(
            "STUDY_TASK_DUPLICATE_ID",
            "StudyPlan proposal cannot contain duplicate task IDs.",
        ))

    if any(task.plan_id != plan.plan_id for task in proposal.tasks):
        violations.append(_violation(
            "STUDY_TASK_PLAN_RELATIONSHIP",
            "Every StudyTask must belong to the proposed StudyPlan.",
        ))
    if any(
        not (plan.start_date <= task.task_date <= plan.end_date)
        for task in proposal.tasks
    ):
        violations.append(_violation(
            "STUDY_TASK_DATE_RANGE",
            "Every StudyTask date must be within the StudyPlan date range.",
        ))
    if any(task.context_id not in learner_context_ids for task in proposal.tasks):
        violations.append(_violation(
            "STUDY_TASK_CONTEXT_OWNERSHIP",
            "Every StudyTask context must belong to the snapshot learner.",
        ))
    if plan.context_id is not None and any(
        task.context_id != plan.context_id for task in proposal.tasks
    ):
        violations.append(_violation(
            "STUDY_TASK_CONTEXT_CONSISTENCY",
            "Every StudyTask in a context-specific plan must use the plan context.",
        ))

    return tuple(violations)


def _violation(rule_id: str, message: str) -> RuleViolation:
    return RuleViolation(
        rule_id=rule_id,
        severity=RuleSeverity.ERROR,
        message=message,
    )


def _deduplicate(
    violations: Iterable[RuleViolation],
) -> tuple[RuleViolation, ...]:
    return tuple(dict.fromkeys(violations))
