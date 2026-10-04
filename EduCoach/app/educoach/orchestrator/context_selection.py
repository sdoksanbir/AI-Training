"""Deterministic memory evidence for later context selection."""

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from educoach.models import ContextStatus, GoalStatus, PlanStatus
from educoach.services.snapshot import LearnerMemorySnapshot


class ContextSelectionEvidenceStatus(StrEnum):
    NONE = "none"
    CONSISTENT = "consistent"
    CONFLICTING = "conflicting"


@dataclass(frozen=True)
class ContextSelectionEvidence:
    status: ContextSelectionEvidenceStatus
    candidate_context_ids: tuple[UUID, ...]
    active_goal_context_ids: tuple[UUID, ...]
    active_plan_context_ids: tuple[UUID, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.status, ContextSelectionEvidenceStatus):
            raise ValueError("status must be a ContextSelectionEvidenceStatus")

        fields = (
            self.candidate_context_ids,
            self.active_goal_context_ids,
            self.active_plan_context_ids,
        )
        for values in fields:
            if not isinstance(values, tuple):
                raise ValueError("context ID collections must be tuples")
            if any(not isinstance(value, UUID) for value in values):
                raise ValueError("context ID collections must contain UUID values")
            if len(set(values)) != len(values):
                raise ValueError("context ID collections cannot contain duplicates")
            if values != tuple(sorted(values, key=str)):
                raise ValueError("context ID collections must use canonical order")

        expected_candidates = tuple(
            sorted(
                set(self.active_goal_context_ids)
                | set(self.active_plan_context_ids),
                key=str,
            )
        )
        if self.candidate_context_ids != expected_candidates:
            raise ValueError("candidate context IDs must match source evidence")

        candidate_count = len(self.candidate_context_ids)
        expected_status = (
            ContextSelectionEvidenceStatus.NONE
            if candidate_count == 0
            else ContextSelectionEvidenceStatus.CONSISTENT
            if candidate_count == 1
            else ContextSelectionEvidenceStatus.CONFLICTING
        )
        if self.status != expected_status:
            raise ValueError("status does not match candidate context IDs")


def project_context_selection_evidence(
    snapshot: LearnerMemorySnapshot,
) -> ContextSelectionEvidence:
    """Project context-scoped active goal and plan evidence from memory."""

    learner_id = snapshot.learner.learner_id
    contexts_by_id = {}
    for context in snapshot.contexts:
        if context.context_id in contexts_by_id:
            raise ValueError("snapshot cannot contain duplicate context_id values")
        if context.learner_id != learner_id:
            raise ValueError("context must belong to the snapshot learner")
        contexts_by_id[context.context_id] = context

    active_context_ids = {
        context_id
        for context_id, context in contexts_by_id.items()
        if context.status == ContextStatus.ACTIVE
    }

    goal_context_ids: set[UUID] = set()
    for goal in snapshot.goals:
        if goal.learner_id != learner_id:
            raise ValueError("goal must belong to the snapshot learner")
        if goal.context_id is not None and goal.context_id not in contexts_by_id:
            raise ValueError("goal must reference a snapshot context")
        if (
            goal.status == GoalStatus.ACTIVE
            and goal.context_id in active_context_ids
        ):
            assert goal.context_id is not None
            goal_context_ids.add(goal.context_id)

    plan_context_ids: set[UUID] = set()
    for plan in snapshot.study_plans:
        if plan.learner_id != learner_id:
            raise ValueError("study plan must belong to the snapshot learner")
        if plan.context_id is not None and plan.context_id not in contexts_by_id:
            raise ValueError("study plan must reference a snapshot context")
        if (
            plan.status == PlanStatus.ACTIVE
            and plan.context_id in active_context_ids
        ):
            assert plan.context_id is not None
            plan_context_ids.add(plan.context_id)

    active_goal_context_ids = tuple(sorted(goal_context_ids, key=str))
    active_plan_context_ids = tuple(sorted(plan_context_ids, key=str))
    candidate_context_ids = tuple(
        sorted(goal_context_ids | plan_context_ids, key=str)
    )
    candidate_count = len(candidate_context_ids)
    status = (
        ContextSelectionEvidenceStatus.NONE
        if candidate_count == 0
        else ContextSelectionEvidenceStatus.CONSISTENT
        if candidate_count == 1
        else ContextSelectionEvidenceStatus.CONFLICTING
    )
    return ContextSelectionEvidence(
        status=status,
        candidate_context_ids=candidate_context_ids,
        active_goal_context_ids=active_goal_context_ids,
        active_plan_context_ids=active_plan_context_ids,
    )
