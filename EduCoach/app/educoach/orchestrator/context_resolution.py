"""Deterministic active learner-context and specialty resolution."""

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from educoach.models import LearningContext
from educoach.services.snapshot import LearnerMemorySnapshot
from educoach.specialties import SpecialtyProfile, SpecialtyProfileRegistry


class ActiveContextResolutionStatus(StrEnum):
    RESOLVED = "resolved"
    AMBIGUOUS = "ambiguous"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class ActiveContextResolution:
    status: ActiveContextResolutionStatus
    context: LearningContext | None = None
    specialty: SpecialtyProfile | None = None


def resolve_active_context(
    snapshot: LearnerMemorySnapshot,
    registry: SpecialtyProfileRegistry | None,
    requested_context_id: UUID | None = None,
) -> ActiveContextResolution:
    """Resolve an explicit or unambiguous learner context without inference."""

    contexts_by_id: dict[UUID, LearningContext] = {}
    learner_id = snapshot.learner.learner_id
    for context in snapshot.contexts:
        if context.context_id in contexts_by_id:
            raise ValueError("snapshot cannot contain duplicate context_id values")
        if context.learner_id != learner_id:
            raise ValueError("context must belong to the snapshot learner")
        contexts_by_id[context.context_id] = context

    if requested_context_id is not None:
        context = contexts_by_id.get(requested_context_id)
        if context is None:
            return ActiveContextResolution(
                status=ActiveContextResolutionStatus.UNAVAILABLE
            )
        return _resolved(context, registry)

    if not contexts_by_id:
        return ActiveContextResolution(
            status=ActiveContextResolutionStatus.UNAVAILABLE
        )
    if len(contexts_by_id) > 1:
        return ActiveContextResolution(
            status=ActiveContextResolutionStatus.AMBIGUOUS
        )

    context = next(iter(contexts_by_id.values()))
    return _resolved(context, registry)


def _resolved(
    context: LearningContext,
    registry: SpecialtyProfileRegistry | None,
) -> ActiveContextResolution:
    specialty = registry.resolve_context(context) if registry is not None else None
    return ActiveContextResolution(
        status=ActiveContextResolutionStatus.RESOLVED,
        context=context,
        specialty=specialty,
    )
