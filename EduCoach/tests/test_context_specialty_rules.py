from dataclasses import FrozenInstanceError
from uuid import UUID, uuid4

import pytest

from educoach.models import ContextType, Learner, LearningContext
from educoach.rules import (
    ContextSpecialtyFact,
    project_context_specialty_facts,
    resolve_context_specialty_fact,
)
from educoach.services.snapshot import LearnerMemorySnapshot
from educoach.specialties import (
    AmbiguousSpecialtyProfileError,
    SpecialtyProfile,
    SpecialtyProfileFamilyMismatchError,
    SpecialtyProfileNotFoundError,
    SpecialtyProfileRegistry,
)


def make_context(
    learner: Learner,
    code: str,
    family: ContextType,
    *,
    context_id: UUID | None = None,
) -> LearningContext:
    values = {
        "learner_id": learner.learner_id,
        "context_type": family,
        "program_code": code,
    }
    if context_id is not None:
        values["context_id"] = context_id
    return LearningContext(**values)


def register_profile(
    registry: SpecialtyProfileRegistry,
    code: str,
    family: ContextType,
    version: int = 1,
) -> None:
    registry.register(
        SpecialtyProfile(
            profile_code=code,
            profile_family=family,
            display_name=code,
            profile_version=version,
        )
    )


def make_snapshot(
    learner: Learner,
    contexts: tuple[LearningContext, ...],
) -> LearnerMemorySnapshot:
    return LearnerMemorySnapshot(
        learner=learner,
        contexts=contexts,
        goals=(),
        availability=(),
        assessments=(),
        assessment_results=(),
        learning_evidence=(),
        study_plans=(),
        study_tasks=(),
        study_sessions=(),
        preferences=(),
        coaching_states=(),
    )


def test_matching_context_resolves_to_identity_fact() -> None:
    learner = Learner()
    context = make_context(learner, "yks", ContextType.ENTRANCE_EXAM)
    registry = SpecialtyProfileRegistry()
    register_profile(registry, "yks", ContextType.ENTRANCE_EXAM)

    fact = resolve_context_specialty_fact(context, registry)

    assert fact == ContextSpecialtyFact(
        context_id=context.context_id,
        learner_id=learner.learner_id,
        context_type=ContextType.ENTRANCE_EXAM,
        program_code="yks",
        profile_code="yks",
        profile_family=ContextType.ENTRANCE_EXAM,
        profile_version=1,
    )


def test_wrong_family_uses_registry_failure() -> None:
    learner = Learner()
    context = make_context(learner, "yks", ContextType.SCHOOL)
    registry = SpecialtyProfileRegistry()
    register_profile(registry, "yks", ContextType.ENTRANCE_EXAM)

    with pytest.raises(SpecialtyProfileFamilyMismatchError):
        resolve_context_specialty_fact(context, registry)


def test_missing_profile_uses_registry_failure() -> None:
    learner = Learner()
    context = make_context(learner, "unknown", ContextType.OTHER)

    with pytest.raises(SpecialtyProfileNotFoundError):
        resolve_context_specialty_fact(context, SpecialtyProfileRegistry())


def test_ambiguous_profile_uses_registry_failure() -> None:
    learner = Learner()
    context = make_context(learner, "yks", ContextType.ENTRANCE_EXAM)
    registry = SpecialtyProfileRegistry()
    register_profile(registry, "yks", ContextType.ENTRANCE_EXAM, version=1)
    register_profile(registry, "yks", ContextType.ENTRANCE_EXAM, version=2)

    with pytest.raises(AmbiguousSpecialtyProfileError):
        resolve_context_specialty_fact(context, registry)


def test_multiple_contexts_resolve_independently_and_deterministically() -> None:
    learner = Learner()
    school = make_context(
        learner,
        "school_7",
        ContextType.SCHOOL,
        context_id=UUID(int=2),
    )
    exam = make_context(
        learner,
        "yks",
        ContextType.ENTRANCE_EXAM,
        context_id=UUID(int=1),
    )
    registry = SpecialtyProfileRegistry()
    register_profile(registry, "school_7", ContextType.SCHOOL)
    register_profile(registry, "yks", ContextType.ENTRANCE_EXAM)

    facts = project_context_specialty_facts(
        make_snapshot(learner, (school, exam)),
        registry,
    )

    assert tuple(fact.context_id for fact in facts) == (
        exam.context_id,
        school.context_id,
    )
    assert tuple(fact.profile_code for fact in facts) == ("yks", "school_7")


def test_snapshot_context_for_another_learner_is_rejected() -> None:
    learner = Learner()
    context = make_context(Learner(), "yks", ContextType.ENTRANCE_EXAM)

    with pytest.raises(ValueError, match="snapshot learner"):
        project_context_specialty_facts(
            make_snapshot(learner, (context,)),
            SpecialtyProfileRegistry(),
        )


def test_context_specialty_fact_is_immutable() -> None:
    learner = Learner()
    context = make_context(learner, "yks", ContextType.ENTRANCE_EXAM)
    registry = SpecialtyProfileRegistry()
    register_profile(registry, "yks", ContextType.ENTRANCE_EXAM)
    fact = resolve_context_specialty_fact(context, registry)

    with pytest.raises(FrozenInstanceError):
        fact.profile_code = "changed"
