"""Minimal rule-layer facts backed by specialty profile resolution."""

from dataclasses import dataclass
from uuid import UUID

from educoach.models import ContextType, LearningContext
from educoach.services.snapshot import LearnerMemorySnapshot
from educoach.specialties import SpecialtyProfileRegistry


@dataclass(frozen=True)
class ContextSpecialtyFact:
    context_id: UUID
    learner_id: UUID
    context_type: ContextType
    program_code: str
    profile_code: str
    profile_family: ContextType
    profile_version: int


def resolve_context_specialty_fact(
    context: LearningContext,
    registry: SpecialtyProfileRegistry,
) -> ContextSpecialtyFact:
    """Resolve one context through the authoritative specialty registry."""

    profile = registry.resolve_context(context)
    return ContextSpecialtyFact(
        context_id=context.context_id,
        learner_id=context.learner_id,
        context_type=context.context_type,
        program_code=context.program_code,
        profile_code=profile.profile_code,
        profile_family=profile.profile_family,
        profile_version=profile.profile_version,
    )


def project_context_specialty_facts(
    snapshot: LearnerMemorySnapshot,
    registry: SpecialtyProfileRegistry,
) -> tuple[ContextSpecialtyFact, ...]:
    """Resolve each learner context independently and deterministically."""

    context_ids: set[UUID] = set()
    facts: list[ContextSpecialtyFact] = []

    for context in snapshot.contexts:
        if context.context_id in context_ids:
            raise ValueError("snapshot cannot contain duplicate context_id values")
        if context.learner_id != snapshot.learner.learner_id:
            raise ValueError("context must belong to the snapshot learner")
        context_ids.add(context.context_id)
        facts.append(resolve_context_specialty_fact(context, registry))

    return tuple(sorted(facts, key=lambda fact: str(fact.context_id)))
