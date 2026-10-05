from dataclasses import FrozenInstanceError
from datetime import date
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest

import educoach.orchestrator.coach as coach_module
from educoach.llm import FakeLLMProvider
from educoach.models import (
    ContextStatus,
    ContextType,
    Goal,
    Learner,
    LearningContext,
    PlanStatus,
    PlanType,
    StudyPlan,
)
from educoach.orchestrator import (
    ActiveContextResolutionStatus,
    CoachOrchestrator,
    ContextRoutingSource,
    FinalContextResolution,
    resolve_request_context,
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


def make_goal(learner: Learner, context: LearningContext) -> Goal:
    return Goal(
        learner_id=learner.learner_id,
        context_id=context.context_id,
        goal_type="study",
        description="Keep studying",
    )


def make_plan(learner: Learner, context: LearningContext) -> StudyPlan:
    return StudyPlan(
        learner_id=learner.learner_id,
        context_id=context.context_id,
        title="Active plan",
        plan_type=PlanType.WEEKLY,
        start_date=date(2026, 10, 5),
        end_date=date(2026, 10, 11),
        status=PlanStatus.ACTIVE,
    )


def make_snapshot(
    learner: Learner,
    contexts: tuple[LearningContext, ...],
    *,
    goals: tuple[Goal, ...] = (),
    plans: tuple[StudyPlan, ...] = (),
) -> LearnerMemorySnapshot:
    return LearnerMemorySnapshot(
        learner=learner,
        contexts=contexts,
        goals=goals,
        availability=(),
        assessments=(),
        assessment_results=(),
        learning_evidence=(),
        study_plans=plans,
        study_tasks=(),
        study_sessions=(),
        preferences=(),
        coaching_states=(),
    )


def make_profile(
    code: str,
    family: ContextType,
    *,
    phrase: str | None = None,
    version: int = 1,
) -> SpecialtyProfile:
    terminology = (
        {"context_routing": {"explicit_phrases": [phrase]}}
        if phrase is not None
        else {}
    )
    return SpecialtyProfile(
        profile_code=code,
        profile_family=family,
        display_name=code,
        profile_version=version,
        terminology=terminology,
    )


def make_registry(*profiles: SpecialtyProfile) -> SpecialtyProfileRegistry:
    registry = SpecialtyProfileRegistry()
    for profile in profiles:
        registry.register(profile)
    return registry


def make_two_context_case() -> tuple[
    Learner,
    LearningContext,
    LearningContext,
    SpecialtyProfileRegistry,
]:
    learner = Learner()
    school = make_context(
        learner,
        "school_program",
        ContextType.SCHOOL,
        context_id=UUID(int=1),
    )
    exam = make_context(
        learner,
        "exam_program",
        ContextType.ENTRANCE_EXAM,
        context_id=UUID(int=2),
    )
    registry = make_registry(
        make_profile("school_program", ContextType.SCHOOL, phrase="school signal"),
        make_profile(
            "exam_program", ContextType.ENTRANCE_EXAM, phrase="exam signal"
        ),
    )
    return learner, school, exam, registry


def test_explicit_valid_context_is_resolved_without_message_override() -> None:
    learner, school, exam, registry = make_two_context_case()

    result = resolve_request_context(
        make_snapshot(learner, (school, exam)),
        "exam signal",
        registry,
        requested_context_id=school.context_id,
    )

    assert result.status == ActiveContextResolutionStatus.RESOLVED
    assert result.context == school
    assert result.source == ContextRoutingSource.EXPLICIT


def test_missing_explicit_context_is_unavailable_without_fallback() -> None:
    learner, school, exam, registry = make_two_context_case()

    result = resolve_request_context(
        make_snapshot(learner, (school, exam), goals=(make_goal(learner, exam),)),
        "exam signal",
        registry,
        requested_context_id=uuid4(),
    )

    assert result == FinalContextResolution(
        ActiveContextResolutionStatus.UNAVAILABLE,
        None,
        None,
        ContextRoutingSource.EXPLICIT,
    )


@pytest.mark.parametrize("status", [ContextStatus.INACTIVE, ContextStatus.COMPLETED])
def test_non_active_explicit_context_is_unavailable(status: ContextStatus) -> None:
    learner = Learner()
    requested = make_context(
        learner,
        "historical",
        ContextType.OTHER,
        status=status,
    )
    active = make_context(learner, "active", ContextType.OTHER)

    result = resolve_request_context(
        make_snapshot(learner, (active, requested)),
        "anything",
        None,
        requested_context_id=requested.context_id,
    )

    assert result.status == ActiveContextResolutionStatus.UNAVAILABLE
    assert result.source == ContextRoutingSource.EXPLICIT


def test_zero_active_contexts_are_unavailable() -> None:
    learner = Learner()
    context = make_context(
        learner,
        "past",
        ContextType.OTHER,
        status=ContextStatus.COMPLETED,
    )

    result = resolve_request_context(make_snapshot(learner, (context,)), "message", None)

    assert result.status == ActiveContextResolutionStatus.UNAVAILABLE
    assert result.source == ContextRoutingSource.NONE


def test_single_active_context_is_resolved_without_evidence_inference() -> None:
    learner = Learner()
    context = make_context(learner, "only", ContextType.OTHER)

    result = resolve_request_context(make_snapshot(learner, (context,)), "", None)

    assert result.status == ActiveContextResolutionStatus.RESOLVED
    assert result.context == context
    assert result.source == ContextRoutingSource.SINGLE_ACTIVE


@pytest.mark.parametrize("memory_case", ["none", "same", "other", "conflicting"])
def test_consistent_message_evidence_outranks_all_memory_states(
    memory_case: str,
) -> None:
    learner, school, exam, registry = make_two_context_case()
    goals = {
        "none": (),
        "same": (make_goal(learner, exam),),
        "other": (make_goal(learner, school),),
        "conflicting": (make_goal(learner, school), make_goal(learner, exam)),
    }[memory_case]

    result = resolve_request_context(
        make_snapshot(learner, (school, exam), goals=goals),
        "exam signal",
        registry,
    )

    assert result.status == ActiveContextResolutionStatus.RESOLVED
    assert result.context == exam
    assert result.source == ContextRoutingSource.MESSAGE_EVIDENCE


@pytest.mark.parametrize("memory_case", ["none", "consistent", "conflicting"])
def test_conflicting_message_evidence_is_always_ambiguous(
    memory_case: str,
) -> None:
    learner, school, exam, registry = make_two_context_case()
    goals = {
        "none": (),
        "consistent": (make_goal(learner, exam),),
        "conflicting": (make_goal(learner, school), make_goal(learner, exam)),
    }[memory_case]

    result = resolve_request_context(
        make_snapshot(learner, (school, exam), goals=goals),
        "school signal and exam signal",
        registry,
    )

    assert result.status == ActiveContextResolutionStatus.AMBIGUOUS
    assert result.source == ContextRoutingSource.NONE


@pytest.mark.parametrize(
    ("memory_case", "expected_status", "expected_source"),
    [
        (
            "consistent",
            ActiveContextResolutionStatus.RESOLVED,
            ContextRoutingSource.MEMORY_EVIDENCE,
        ),
        (
            "none",
            ActiveContextResolutionStatus.AMBIGUOUS,
            ContextRoutingSource.NONE,
        ),
        (
            "conflicting",
            ActiveContextResolutionStatus.AMBIGUOUS,
            ContextRoutingSource.NONE,
        ),
    ],
)
def test_message_none_uses_memory_only_when_consistent(
    memory_case: str,
    expected_status: ActiveContextResolutionStatus,
    expected_source: ContextRoutingSource,
) -> None:
    learner, school, exam, registry = make_two_context_case()
    goals = {
        "consistent": (make_goal(learner, exam),),
        "none": (),
        "conflicting": (make_goal(learner, school), make_goal(learner, exam)),
    }[memory_case]

    result = resolve_request_context(
        make_snapshot(learner, (school, exam), goals=goals),
        "no routing terminology here",
        registry,
    )

    assert result.status == expected_status
    assert result.source == expected_source
    assert result.context == (exam if memory_case == "consistent" else None)


def test_registry_none_still_allows_consistent_memory_routing() -> None:
    learner, school, exam, _ = make_two_context_case()

    result = resolve_request_context(
        make_snapshot(learner, (school, exam), goals=(make_goal(learner, exam),)),
        "exam signal",
        None,
    )

    assert result.context == exam
    assert result.specialty is None
    assert result.source == ContextRoutingSource.MEMORY_EVIDENCE


def test_registry_none_without_memory_evidence_is_ambiguous() -> None:
    learner, school, exam, _ = make_two_context_case()

    result = resolve_request_context(
        make_snapshot(learner, (school, exam)), "exam signal", None
    )

    assert result.status == ActiveContextResolutionStatus.AMBIGUOUS


def test_final_result_is_immutable() -> None:
    learner = Learner()
    context = make_context(learner, "only", ContextType.OTHER)
    result = resolve_request_context(make_snapshot(learner, (context,)), "", None)

    with pytest.raises(FrozenInstanceError):
        result.source = ContextRoutingSource.NONE


def test_invalid_resolved_direct_construction_is_rejected() -> None:
    with pytest.raises(ValueError, match="requires a context"):
        FinalContextResolution(
            ActiveContextResolutionStatus.RESOLVED,
            None,
            None,
            ContextRoutingSource.SINGLE_ACTIVE,
        )


def test_invalid_ambiguous_direct_construction_is_rejected() -> None:
    learner = Learner()
    context = make_context(learner, "active", ContextType.OTHER)

    with pytest.raises(ValueError, match="cannot carry"):
        FinalContextResolution(
            ActiveContextResolutionStatus.AMBIGUOUS,
            context,
            None,
            ContextRoutingSource.NONE,
        )


def test_invalid_unavailable_direct_construction_is_rejected() -> None:
    with pytest.raises(ValueError, match="invalid source"):
        FinalContextResolution(
            ActiveContextResolutionStatus.UNAVAILABLE,
            None,
            None,
            ContextRoutingSource.MESSAGE_EVIDENCE,
        )


def test_context_goal_and_plan_order_do_not_change_routing() -> None:
    learner, school, exam, registry = make_two_context_case()
    school_goals = (make_goal(learner, school), make_goal(learner, school))
    exam_plans = (make_plan(learner, exam), make_plan(learner, exam))
    forward = resolve_request_context(
        make_snapshot(
            learner,
            (school, exam),
            goals=school_goals,
            plans=exam_plans,
        ),
        "no evidence",
        registry,
    )
    reverse = resolve_request_context(
        make_snapshot(
            learner,
            (exam, school),
            goals=tuple(reversed(school_goals)),
            plans=tuple(reversed(exam_plans)),
        ),
        "no evidence",
        registry,
    )

    assert forward == reverse
    assert forward.status == ActiveContextResolutionStatus.AMBIGUOUS


def test_registry_registration_order_does_not_change_routing() -> None:
    learner, school, exam, registry = make_two_context_case()
    profiles = tuple(registry.list_profiles())
    reverse_registry = make_registry(*reversed(profiles))
    snapshot = make_snapshot(learner, (school, exam))

    forward = resolve_request_context(snapshot, "exam signal", registry)
    reverse = resolve_request_context(snapshot, "exam signal", reverse_registry)

    assert forward == reverse


def test_selected_specialty_is_resolved_authoritatively() -> None:
    learner, school, exam, registry = make_two_context_case()

    result = resolve_request_context(
        make_snapshot(learner, (school, exam)), "exam signal", registry
    )

    assert result.specialty == registry.resolve_context(exam)


def test_missing_specialty_error_propagates_when_resolution_requires_it() -> None:
    learner = Learner()
    context = make_context(learner, "missing", ContextType.OTHER)

    with pytest.raises(SpecialtyProfileNotFoundError):
        resolve_request_context(
            make_snapshot(learner, (context,)), "message", SpecialtyProfileRegistry()
        )


def test_specialty_family_mismatch_error_propagates() -> None:
    learner = Learner()
    context = make_context(learner, "mismatch", ContextType.SCHOOL)
    registry = make_registry(make_profile("mismatch", ContextType.OTHER))

    with pytest.raises(SpecialtyProfileFamilyMismatchError):
        resolve_request_context(make_snapshot(learner, (context,)), "message", registry)


def test_specialty_ambiguity_error_propagates() -> None:
    learner = Learner()
    context = make_context(learner, "versioned", ContextType.OTHER)
    registry = make_registry(
        make_profile("versioned", ContextType.OTHER, version=1),
        make_profile("versioned", ContextType.OTHER, version=2),
    )

    with pytest.raises(AmbiguousSpecialtyProfileError):
        resolve_request_context(make_snapshot(learner, (context,)), "message", registry)


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


def make_runtime(
    snapshot: LearnerMemorySnapshot,
    registry: SpecialtyProfileRegistry | None,
) -> tuple[CoachOrchestrator, RecordingRetriever, FakeLLMProvider]:
    memory = Mock(spec=LearnerMemoryService)
    memory.get_learner_memory_snapshot.return_value = snapshot
    retriever = RecordingRetriever()
    provider = FakeLLMProvider(responder=lambda _: "Birlikte inceleyelim.")
    orchestrator = CoachOrchestrator(
        memory,
        provider,
        retriever,
        specialty_registry=registry,
    )
    return orchestrator, retriever, provider


def test_runtime_message_routes_multi_active_scope_to_selected_program_only() -> None:
    learner, school, exam, registry = make_two_context_case()
    orchestrator, retriever, provider = make_runtime(
        make_snapshot(learner, (school, exam), goals=(make_goal(learner, school),)),
        registry,
    )

    orchestrator.respond(learner.learner_id, "exam signal")

    assert retriever.filters == [{"program": {"global", "exam_program"}}]
    assert "school_program" not in retriever.filters[0]["program"]
    assert len(provider.requests) == 1


def test_runtime_memory_routes_when_message_has_no_signal() -> None:
    learner, school, exam, registry = make_two_context_case()
    orchestrator, retriever, _ = make_runtime(
        make_snapshot(learner, (school, exam), goals=(make_goal(learner, school),)),
        registry,
    )

    orchestrator.respond(learner.learner_id, "general request")

    assert retriever.filters == [{"program": {"global", "school_program"}}]


def test_ambiguous_runtime_returns_clarification_without_downstream_calls(
    monkeypatch,
) -> None:
    learner, school, exam, registry = make_two_context_case()
    orchestrator, retriever, provider = make_runtime(
        make_snapshot(learner, (school, exam)), registry
    )
    monkeypatch.setattr(
        coach_module,
        "validate_response",
        lambda *args, **kwargs: pytest.fail("validator must not be called"),
    )

    result = orchestrator.respond(learner.learner_id, "general request")

    assert result.text == (
        "Birden fazla aktif çalışma bağlamın var. "
        "Hangi bağlamı kastettiğini belirtir misin?"
    )
    assert result.model == "deterministic"
    assert retriever.filters == []
    assert provider.requests == []


def test_runtime_explicit_context_overrides_message_evidence() -> None:
    learner, school, exam, registry = make_two_context_case()
    orchestrator, retriever, _ = make_runtime(
        make_snapshot(learner, (school, exam)), registry
    )

    orchestrator.respond(
        learner.learner_id,
        "exam signal",
        context_id=school.context_id,
    )

    assert retriever.filters == [{"program": {"global", "school_program"}}]


def test_runtime_invalid_explicit_context_stops_before_rag_and_llm() -> None:
    learner, school, exam, registry = make_two_context_case()
    orchestrator, retriever, provider = make_runtime(
        make_snapshot(learner, (school, exam)), registry
    )

    with pytest.raises(ValueError, match="requested context"):
        orchestrator.respond(learner.learner_id, "exam signal", context_id=uuid4())

    assert retriever.filters == []
    assert provider.requests == []


def test_runtime_zero_active_preserves_global_only_rag_and_llm() -> None:
    learner = Learner()
    completed = make_context(
        learner,
        "past",
        ContextType.OTHER,
        status=ContextStatus.COMPLETED,
    )
    orchestrator, retriever, provider = make_runtime(
        make_snapshot(learner, (completed,)), None
    )

    orchestrator.respond(learner.learner_id, "general request")

    assert retriever.filters == [{"program": {"global"}}]
    assert len(provider.requests) == 1


def test_runtime_single_active_preserves_selected_scope() -> None:
    learner = Learner()
    context = make_context(learner, "only", ContextType.OTHER)
    orchestrator, retriever, provider = make_runtime(
        make_snapshot(learner, (context,)), None
    )

    orchestrator.respond(learner.learner_id, "general request")

    assert retriever.filters == [{"program": {"global", "only"}}]
    assert len(provider.requests) == 1


def test_runtime_invokes_intent_detection_only_after_context_resolution(
    monkeypatch,
) -> None:
    learner = Learner()
    context = make_context(learner, "only", ContextType.OTHER)
    orchestrator, _, _ = make_runtime(make_snapshot(learner, (context,)), None)
    detector = Mock(return_value=coach_module.detect_intents("general request"))
    monkeypatch.setattr(
        coach_module,
        "detect_intents",
        detector,
    )

    orchestrator.respond(learner.learner_id, "general request")

    detector.assert_called_once_with("general request")
