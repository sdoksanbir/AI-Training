from dataclasses import FrozenInstanceError
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest

from educoach.llm import FakeLLMProvider
from educoach.models import (
    ContextStatus,
    ContextType,
    Learner,
    LearningContext,
)
from educoach.orchestrator import (
    ActiveContextResolutionStatus,
    CoachOrchestrator,
    resolve_active_context,
)
from educoach.services import LearnerMemoryService, LearnerMemorySnapshot
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
    status: ContextStatus = ContextStatus.ACTIVE,
) -> LearningContext:
    values = {
        "learner_id": learner.learner_id,
        "context_type": family,
        "program_code": code,
        "status": status,
    }
    if context_id is not None:
        values["context_id"] = context_id
    return LearningContext(**values)


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


def register_profile(
    registry: SpecialtyProfileRegistry,
    code: str,
    family: ContextType,
    *,
    version: int = 1,
) -> SpecialtyProfile:
    profile = SpecialtyProfile(
        profile_code=code,
        profile_family=family,
        display_name=code,
        profile_version=version,
    )
    registry.register(profile)
    return profile


def test_no_context_is_unavailable() -> None:
    learner = Learner()

    result = resolve_active_context(
        make_snapshot(learner, ()),
        SpecialtyProfileRegistry(),
    )

    assert result.status == ActiveContextResolutionStatus.UNAVAILABLE
    assert result.context is None
    assert result.specialty is None


def test_single_context_resolves_context_and_authoritative_specialty() -> None:
    learner = Learner()
    context = make_context(learner, "yks", ContextType.ENTRANCE_EXAM)
    registry = SpecialtyProfileRegistry()
    profile = register_profile(registry, "yks", ContextType.ENTRANCE_EXAM)

    result = resolve_active_context(make_snapshot(learner, (context,)), registry)

    assert result.status == ActiveContextResolutionStatus.RESOLVED
    assert result.context == context
    assert result.specialty == profile


@pytest.mark.parametrize(
    "status",
    [ContextStatus.INACTIVE, ContextStatus.COMPLETED],
)
def test_single_non_active_context_is_unavailable(
    status: ContextStatus,
) -> None:
    learner = Learner()
    context = make_context(
        learner,
        "yks",
        ContextType.ENTRANCE_EXAM,
        status=status,
    )
    registry = Mock(spec=SpecialtyProfileRegistry)

    result = resolve_active_context(make_snapshot(learner, (context,)), registry)

    assert result.status == ActiveContextResolutionStatus.UNAVAILABLE
    assert result.context is None
    assert result.specialty is None
    registry.resolve_context.assert_not_called()


@pytest.mark.parametrize(
    "other_status",
    [ContextStatus.INACTIVE, ContextStatus.COMPLETED],
)
def test_non_active_context_does_not_make_single_active_context_ambiguous(
    other_status: ContextStatus,
) -> None:
    learner = Learner()
    active = make_context(learner, "yks", ContextType.ENTRANCE_EXAM)
    historical = make_context(
        learner,
        "school_11",
        ContextType.SCHOOL,
        status=other_status,
    )
    registry = SpecialtyProfileRegistry()
    profile = register_profile(registry, "yks", ContextType.ENTRANCE_EXAM)

    result = resolve_active_context(
        make_snapshot(learner, (historical, active)), registry
    )

    assert result.status == ActiveContextResolutionStatus.RESOLVED
    assert result.context == active
    assert result.specialty == profile


def test_two_active_contexts_remain_ambiguous_with_inactive_history() -> None:
    learner = Learner()
    first = make_context(learner, "school_11", ContextType.SCHOOL)
    second = make_context(learner, "yks", ContextType.ENTRANCE_EXAM)
    inactive = make_context(
        learner,
        "general_english",
        ContextType.LANGUAGE_LEARNING,
        status=ContextStatus.INACTIVE,
    )

    result = resolve_active_context(
        make_snapshot(learner, (inactive, second, first)),
        SpecialtyProfileRegistry(),
    )

    assert result.status == ActiveContextResolutionStatus.AMBIGUOUS


def test_multiple_contexts_without_request_are_ambiguous_in_any_order() -> None:
    learner = Learner()
    school = make_context(
        learner, "school_11", ContextType.SCHOOL, context_id=UUID(int=2)
    )
    exam = make_context(
        learner, "yks", ContextType.ENTRANCE_EXAM, context_id=UUID(int=1)
    )
    registry = SpecialtyProfileRegistry()

    forward = resolve_active_context(
        make_snapshot(learner, (school, exam)), registry
    )
    reverse = resolve_active_context(
        make_snapshot(learner, (exam, school)), registry
    )

    assert forward == reverse
    assert forward.status == ActiveContextResolutionStatus.AMBIGUOUS
    assert forward.context is None


def test_explicit_context_resolves_correct_context_and_specialty() -> None:
    learner = Learner()
    school = make_context(learner, "school_11", ContextType.SCHOOL)
    exam = make_context(learner, "yks", ContextType.ENTRANCE_EXAM)
    registry = SpecialtyProfileRegistry()
    register_profile(registry, "school_11", ContextType.SCHOOL)
    exam_profile = register_profile(
        registry, "yks", ContextType.ENTRANCE_EXAM
    )

    result = resolve_active_context(
        make_snapshot(learner, (school, exam)),
        registry,
        requested_context_id=exam.context_id,
    )

    assert result.status == ActiveContextResolutionStatus.RESOLVED
    assert result.context == exam
    assert result.specialty == exam_profile


def test_missing_explicit_context_never_falls_back() -> None:
    learner = Learner()
    context = make_context(learner, "yks", ContextType.ENTRANCE_EXAM)
    registry = SpecialtyProfileRegistry()
    register_profile(registry, "yks", ContextType.ENTRANCE_EXAM)

    result = resolve_active_context(
        make_snapshot(learner, (context,)),
        registry,
        requested_context_id=uuid4(),
    )

    assert result.status == ActiveContextResolutionStatus.UNAVAILABLE
    assert result.context is None
    assert result.specialty is None


@pytest.mark.parametrize(
    "status",
    [ContextStatus.INACTIVE, ContextStatus.COMPLETED],
)
def test_explicit_non_active_context_is_unavailable_without_fallback(
    status: ContextStatus,
) -> None:
    learner = Learner()
    active = make_context(learner, "yks", ContextType.ENTRANCE_EXAM)
    requested = make_context(
        learner,
        "school_11",
        ContextType.SCHOOL,
        status=status,
    )
    registry = Mock(spec=SpecialtyProfileRegistry)

    result = resolve_active_context(
        make_snapshot(learner, (active, requested)),
        registry,
        requested_context_id=requested.context_id,
    )

    assert result.status == ActiveContextResolutionStatus.UNAVAILABLE
    assert result.context is None
    assert result.specialty is None
    registry.resolve_context.assert_not_called()


def test_inactive_foreign_context_still_fails_ownership_validation() -> None:
    learner = Learner()
    foreign = make_context(
        Learner(),
        "yks",
        ContextType.ENTRANCE_EXAM,
        status=ContextStatus.INACTIVE,
    )

    with pytest.raises(ValueError, match="snapshot learner"):
        resolve_active_context(
            make_snapshot(learner, (foreign,)),
            SpecialtyProfileRegistry(),
        )


def test_completed_duplicate_context_id_still_fails_integrity_validation() -> None:
    learner = Learner()
    context_id = uuid4()
    first = make_context(
        learner,
        "school_11",
        ContextType.SCHOOL,
        context_id=context_id,
        status=ContextStatus.COMPLETED,
    )
    second = make_context(
        learner,
        "yks",
        ContextType.ENTRANCE_EXAM,
        context_id=context_id,
        status=ContextStatus.COMPLETED,
    )

    with pytest.raises(ValueError, match="duplicate context_id"):
        resolve_active_context(
            make_snapshot(learner, (first, second)),
            SpecialtyProfileRegistry(),
        )


def test_foreign_learner_context_is_rejected() -> None:
    learner = Learner()
    foreign = make_context(Learner(), "yks", ContextType.ENTRANCE_EXAM)

    with pytest.raises(ValueError, match="snapshot learner"):
        resolve_active_context(
            make_snapshot(learner, (foreign,)),
            SpecialtyProfileRegistry(),
        )


def test_duplicate_context_id_is_rejected() -> None:
    learner = Learner()
    context_id = uuid4()
    first = make_context(
        learner, "school_11", ContextType.SCHOOL, context_id=context_id
    )
    second = make_context(
        learner, "yks", ContextType.ENTRANCE_EXAM, context_id=context_id
    )

    with pytest.raises(ValueError, match="duplicate context_id"):
        resolve_active_context(
            make_snapshot(learner, (first, second)),
            SpecialtyProfileRegistry(),
        )


def test_missing_specialty_failure_is_not_hidden() -> None:
    learner = Learner()
    context = make_context(learner, "unknown", ContextType.OTHER)

    with pytest.raises(SpecialtyProfileNotFoundError):
        resolve_active_context(
            make_snapshot(learner, (context,)),
            SpecialtyProfileRegistry(),
        )


def test_specialty_family_mismatch_is_not_hidden() -> None:
    learner = Learner()
    context = make_context(learner, "yks", ContextType.SCHOOL)
    registry = SpecialtyProfileRegistry()
    register_profile(registry, "yks", ContextType.ENTRANCE_EXAM)

    with pytest.raises(SpecialtyProfileFamilyMismatchError):
        resolve_active_context(make_snapshot(learner, (context,)), registry)


def test_specialty_registry_ambiguity_is_not_hidden() -> None:
    learner = Learner()
    context = make_context(learner, "yks", ContextType.ENTRANCE_EXAM)
    registry = SpecialtyProfileRegistry()
    register_profile(registry, "yks", ContextType.ENTRANCE_EXAM, version=1)
    register_profile(registry, "yks", ContextType.ENTRANCE_EXAM, version=2)

    with pytest.raises(AmbiguousSpecialtyProfileError):
        resolve_active_context(make_snapshot(learner, (context,)), registry)


def test_resolver_is_repeatable_and_result_is_immutable() -> None:
    learner = Learner()
    context = make_context(learner, "yks", ContextType.ENTRANCE_EXAM)
    registry = SpecialtyProfileRegistry()
    register_profile(registry, "yks", ContextType.ENTRANCE_EXAM)
    snapshot = make_snapshot(learner, (context,))

    first = resolve_active_context(snapshot, registry)
    second = resolve_active_context(snapshot, registry)

    assert first == second
    with pytest.raises(FrozenInstanceError):
        first.status = ActiveContextResolutionStatus.AMBIGUOUS


class RecordingRetriever:
    def __init__(self) -> None:
        self.filters: list[dict[str, str | set[str]] | None] = []

    def search(
        self,
        query: str,
        limit: int = 3,
        filters: dict[str, str | set[str]] | None = None,
    ) -> list[object]:
        self.filters.append(filters)
        return []


def run_orchestrator(
    snapshot: LearnerMemorySnapshot,
    *,
    registry: SpecialtyProfileRegistry | None = None,
    context_id: UUID | None = None,
) -> tuple[RecordingRetriever, FakeLLMProvider]:
    memory = Mock(spec=LearnerMemoryService)
    memory.get_learner_memory_snapshot.return_value = snapshot
    retriever = RecordingRetriever()
    provider = FakeLLMProvider(responder=lambda _: "Birlikte inceleyelim.")

    CoachOrchestrator(
        memory,
        provider,
        retriever,
        specialty_registry=registry,
    ).respond(
        snapshot.learner.learner_id,
        "Çalışma önerisi",
        context_id=context_id,
    )
    return retriever, provider


def test_single_context_orchestrator_uses_active_program_and_global_only() -> None:
    learner = Learner()
    context = make_context(learner, "yks", ContextType.ENTRANCE_EXAM)

    retriever, _ = run_orchestrator(make_snapshot(learner, (context,)))

    assert retriever.filters == [{"program": {"yks", "global"}}]


def test_orchestrator_ignores_inactive_context_when_one_context_is_active() -> None:
    learner = Learner()
    active = make_context(learner, "yks", ContextType.ENTRANCE_EXAM)
    inactive = make_context(
        learner,
        "school_11",
        ContextType.SCHOOL,
        status=ContextStatus.INACTIVE,
    )

    retriever, _ = run_orchestrator(
        make_snapshot(learner, (inactive, active))
    )

    assert retriever.filters == [{"program": {"yks", "global"}}]


def test_orchestrator_uses_global_only_when_no_context_is_active() -> None:
    learner = Learner()
    inactive = make_context(
        learner,
        "school_11",
        ContextType.SCHOOL,
        status=ContextStatus.INACTIVE,
    )
    completed = make_context(
        learner,
        "yks",
        ContextType.ENTRANCE_EXAM,
        status=ContextStatus.COMPLETED,
    )

    retriever, _ = run_orchestrator(
        make_snapshot(learner, (inactive, completed))
    )

    assert retriever.filters == [{"program": {"global"}}]


def test_ambiguous_orchestrator_uses_global_only() -> None:
    learner = Learner()
    school = make_context(learner, "school_11", ContextType.SCHOOL)
    exam = make_context(learner, "yks", ContextType.ENTRANCE_EXAM)

    retriever, _ = run_orchestrator(
        make_snapshot(learner, (school, exam))
    )

    assert retriever.filters == [{"program": {"global"}}]


def test_explicit_context_is_connected_to_orchestrator_filter() -> None:
    learner = Learner()
    school = make_context(learner, "school_11", ContextType.SCHOOL)
    exam = make_context(learner, "yks", ContextType.ENTRANCE_EXAM)
    registry = SpecialtyProfileRegistry()
    register_profile(registry, "school_11", ContextType.SCHOOL)
    register_profile(registry, "yks", ContextType.ENTRANCE_EXAM)

    retriever, _ = run_orchestrator(
        make_snapshot(learner, (school, exam)),
        registry=registry,
        context_id=exam.context_id,
    )

    assert retriever.filters == [{"program": {"yks", "global"}}]


def test_missing_explicit_context_stops_before_rag_and_llm() -> None:
    learner = Learner()
    context = make_context(learner, "yks", ContextType.ENTRANCE_EXAM)
    snapshot = make_snapshot(learner, (context,))
    memory = Mock(spec=LearnerMemoryService)
    memory.get_learner_memory_snapshot.return_value = snapshot
    retriever = RecordingRetriever()
    provider = FakeLLMProvider()

    with pytest.raises(ValueError, match="requested context"):
        CoachOrchestrator(memory, provider, retriever).respond(
            learner.learner_id,
            "Çalışma önerisi",
            context_id=uuid4(),
        )

    assert retriever.filters == []
    assert provider.requests == []


@pytest.mark.parametrize(
    "status",
    [ContextStatus.INACTIVE, ContextStatus.COMPLETED],
)
def test_explicit_non_active_context_stops_before_rag_and_llm(
    status: ContextStatus,
) -> None:
    learner = Learner()
    context = make_context(
        learner,
        "yks",
        ContextType.ENTRANCE_EXAM,
        status=status,
    )
    snapshot = make_snapshot(learner, (context,))
    memory = Mock(spec=LearnerMemoryService)
    memory.get_learner_memory_snapshot.return_value = snapshot
    retriever = RecordingRetriever()
    provider = FakeLLMProvider()

    with pytest.raises(ValueError, match="requested context"):
        CoachOrchestrator(memory, provider, retriever).respond(
            learner.learner_id,
            "Çalışma önerisi",
            context_id=context.context_id,
        )

    assert retriever.filters == []
    assert provider.requests == []
