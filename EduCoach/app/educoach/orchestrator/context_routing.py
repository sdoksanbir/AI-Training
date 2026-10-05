"""Deterministic final request-context routing policy."""

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from educoach.models import ContextStatus, LearningContext
from educoach.services import LearnerMemorySnapshot
from educoach.specialties import SpecialtyProfile, SpecialtyProfileRegistry

from .context_message_evidence import (
    MessageContextEvidenceStatus,
    project_message_context_evidence,
)
from .context_resolution import (
    ActiveContextResolution,
    ActiveContextResolutionStatus,
    resolve_active_context,
)
from .context_selection import (
    ContextSelectionEvidenceStatus,
    project_context_selection_evidence,
)


class ContextRoutingSource(StrEnum):
    EXPLICIT = "explicit"
    SINGLE_ACTIVE = "single_active"
    MESSAGE_EVIDENCE = "message_evidence"
    MEMORY_EVIDENCE = "memory_evidence"
    NONE = "none"


@dataclass(frozen=True)
class FinalContextResolution:
    status: ActiveContextResolutionStatus
    context: LearningContext | None
    specialty: SpecialtyProfile | None
    source: ContextRoutingSource

    def __post_init__(self) -> None:
        if not isinstance(self.status, ActiveContextResolutionStatus):
            raise ValueError("status must be an ActiveContextResolutionStatus")
        if not isinstance(self.source, ContextRoutingSource):
            raise ValueError("source must be a ContextRoutingSource")
        if self.context is not None and not isinstance(self.context, LearningContext):
            raise ValueError("context must be a LearningContext or None")
        if self.specialty is not None and not isinstance(
            self.specialty, SpecialtyProfile
        ):
            raise ValueError("specialty must be a SpecialtyProfile or None")

        resolved_sources = {
            ContextRoutingSource.EXPLICIT,
            ContextRoutingSource.SINGLE_ACTIVE,
            ContextRoutingSource.MESSAGE_EVIDENCE,
            ContextRoutingSource.MEMORY_EVIDENCE,
        }
        if self.status == ActiveContextResolutionStatus.RESOLVED:
            if self.context is None:
                raise ValueError("resolved routing requires a context")
            if self.source not in resolved_sources:
                raise ValueError("resolved routing requires a selection source")
            if self.context.status != ContextStatus.ACTIVE:
                raise ValueError("resolved routing requires an active context")
            if self.specialty is not None and (
                self.specialty.profile_code != self.context.program_code
                or self.specialty.profile_family != self.context.context_type
            ):
                raise ValueError("specialty must match the resolved context")
            return

        if self.context is not None or self.specialty is not None:
            raise ValueError("unresolved routing cannot carry context or specialty")
        if self.status == ActiveContextResolutionStatus.AMBIGUOUS:
            if self.source != ContextRoutingSource.NONE:
                raise ValueError("ambiguous routing must use the none source")
            return
        if self.status == ActiveContextResolutionStatus.UNAVAILABLE:
            if self.source not in {
                ContextRoutingSource.EXPLICIT,
                ContextRoutingSource.NONE,
            }:
                raise ValueError("unavailable routing has an invalid source")
            return
        raise ValueError("unsupported context routing status")


def resolve_request_context(
    snapshot: LearnerMemorySnapshot,
    message: str,
    registry: SpecialtyProfileRegistry | None,
    requested_context_id: UUID | None = None,
) -> FinalContextResolution:
    """Resolve the final context without LLM, intent, or history inference.

    An explicit request has absolute precedence. With multiple active contexts,
    strong evidence in the current user message outranks ongoing goal/plan memory
    because the learner may have switched contexts in the current turn. Conflicting
    message evidence is never overridden by memory evidence.
    """

    if not isinstance(message, str):
        raise ValueError("message must be a string")

    active_resolution = resolve_active_context(
        snapshot,
        registry,
        requested_context_id=requested_context_id,
    )

    if requested_context_id is not None:
        return _from_active_resolution(
            active_resolution,
            resolved_source=ContextRoutingSource.EXPLICIT,
            unresolved_source=ContextRoutingSource.EXPLICIT,
        )

    if active_resolution.status == ActiveContextResolutionStatus.UNAVAILABLE:
        return _from_active_resolution(
            active_resolution,
            resolved_source=ContextRoutingSource.SINGLE_ACTIVE,
            unresolved_source=ContextRoutingSource.NONE,
        )
    if active_resolution.status == ActiveContextResolutionStatus.RESOLVED:
        return _from_active_resolution(
            active_resolution,
            resolved_source=ContextRoutingSource.SINGLE_ACTIVE,
            unresolved_source=ContextRoutingSource.NONE,
        )

    contexts_by_id = {context.context_id: context for context in snapshot.contexts}

    if registry is not None:
        message_evidence = project_message_context_evidence(
            message,
            snapshot,
            registry,
        )
        if message_evidence.status == MessageContextEvidenceStatus.CONSISTENT:
            return _resolved_from_context_id(
                message_evidence.candidate_context_ids[0],
                contexts_by_id,
                registry,
                ContextRoutingSource.MESSAGE_EVIDENCE,
            )
        if message_evidence.status == MessageContextEvidenceStatus.CONFLICTING:
            return _ambiguous()

    memory_evidence = project_context_selection_evidence(snapshot)
    if memory_evidence.status == ContextSelectionEvidenceStatus.CONSISTENT:
        return _resolved_from_context_id(
            memory_evidence.candidate_context_ids[0],
            contexts_by_id,
            registry,
            ContextRoutingSource.MEMORY_EVIDENCE,
        )
    return _ambiguous()


def _from_active_resolution(
    resolution: ActiveContextResolution,
    *,
    resolved_source: ContextRoutingSource,
    unresolved_source: ContextRoutingSource,
) -> FinalContextResolution:
    source = (
        resolved_source
        if resolution.status == ActiveContextResolutionStatus.RESOLVED
        else unresolved_source
    )
    return FinalContextResolution(
        status=resolution.status,
        context=resolution.context,
        specialty=resolution.specialty,
        source=source,
    )


def _resolved_from_context_id(
    context_id: UUID,
    contexts_by_id: dict[UUID, LearningContext],
    registry: SpecialtyProfileRegistry | None,
    source: ContextRoutingSource,
) -> FinalContextResolution:
    context = contexts_by_id[context_id]
    specialty = registry.resolve_context(context) if registry is not None else None
    return FinalContextResolution(
        status=ActiveContextResolutionStatus.RESOLVED,
        context=context,
        specialty=specialty,
        source=source,
    )


def _ambiguous() -> FinalContextResolution:
    return FinalContextResolution(
        status=ActiveContextResolutionStatus.AMBIGUOUS,
        context=None,
        specialty=None,
        source=ContextRoutingSource.NONE,
    )
