from dataclasses import FrozenInstanceError
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
)
from educoach.orchestrator import (
    CoachOrchestrator,
    IntentResolution,
    IntentResolutionStatus,
    IntentType,
    RAGNeedDecision,
    RAGNeedSource,
    RAGNeedStatus,
    decide_rag_need,
    detect_intents,
    resolve_intents,
)
from educoach.services import LearnerMemoryService, LearnerMemorySnapshot
from educoach.specialties import SpecialtyProfile, SpecialtyProfileRegistry


@pytest.mark.parametrize(
    "intent",
    [IntentType.KNOWLEDGE_QUESTION, IntentType.STUDY_ADVICE],
)
def test_required_intents_require_rag(intent: IntentType) -> None:
    decision = decide_rag_need("request", resolve_intents((intent,)))

    assert decision.status == RAGNeedStatus.REQUIRED
    assert decision.intents == (intent,)
    assert decision.source == RAGNeedSource.REQUIRED_INTENT


@pytest.mark.parametrize(
    "intent",
    [
        IntentType.GENERAL_CONVERSATION,
        IntentType.MOTIVATION_SUPPORT,
        IntentType.GOAL_SETTING,
        IntentType.ASSESSMENT_ANALYSIS,
        IntentType.PROGRESS_REVIEW,
        IntentType.MEMORY_UPDATE,
        IntentType.TASK_UPDATE,
        IntentType.CLARIFICATION,
        IntentType.PLANNING,
    ],
)
def test_local_intents_do_not_require_rag(intent: IntentType) -> None:
    decision = decide_rag_need("request", resolve_intents((intent,)))

    assert decision.status == RAGNeedStatus.NOT_REQUIRED
    assert decision.intents == (intent,)
    assert decision.source == RAGNeedSource.LOCAL_INTENT


@pytest.mark.parametrize(
    "local_intent",
    [IntentType.PLANNING, IntentType.ASSESSMENT_ANALYSIS],
)
def test_required_intent_wins_in_multi_intent_request(
    local_intent: IntentType,
) -> None:
    resolution = resolve_intents((local_intent, IntentType.STUDY_ADVICE))

    decision = decide_rag_need("request", resolution)

    assert decision.status == RAGNeedStatus.REQUIRED
    assert decision.source == RAGNeedSource.REQUIRED_INTENT


def test_unresolved_intent_remains_unresolved() -> None:
    decision = decide_rag_need("request", resolve_intents(()))

    assert decision == RAGNeedDecision(
        RAGNeedStatus.UNRESOLVED,
        (),
        RAGNeedSource.UNRESOLVED,
    )


@pytest.mark.parametrize(
    "message",
    [
        "Bu konuya başlamadan önce hangi konuları bilmeliyim?",
        "Bu sınavın güncel yapısı nedir?",
        "Aralıklı tekrar nasıl yapılır?",
    ],
)
def test_high_precision_external_knowledge_signals_require_rag(
    message: str,
) -> None:
    decision = decide_rag_need(message, detect_intents(message))

    assert decision.status == RAGNeedStatus.REQUIRED
    assert decision.source == RAGNeedSource.EXTERNAL_KNOWLEDGE_SIGNAL


def test_plan_adjustment_signal_is_not_required_when_detector_is_unresolved() -> None:
    message = "Bugün 3 saatim var, programımı 3 saate indir."
    resolution = detect_intents(message)

    assert resolution.status == IntentResolutionStatus.UNRESOLVED
    assert decide_rag_need(message, resolution) == RAGNeedDecision(
        RAGNeedStatus.NOT_REQUIRED,
        (),
        RAGNeedSource.PLAN_ADJUSTMENT_SIGNAL,
    )


@pytest.mark.parametrize(
    "message",
    [
        "BU SINAVIN GÜNCEL YAPISI NEDİR?!",
        "Bu konuya başlamadan önce, hangi konuları bilmeliyim?!",
        "ARALIKLI TEKRAR: NASIL YAPILIR?",
    ],
)
def test_external_signal_normalization_handles_turkish_case_and_punctuation(
    message: str,
) -> None:
    assert decide_rag_need(message, detect_intents(message)).status == (
        RAGNeedStatus.REQUIRED
    )


def test_unrelated_how_word_alone_is_not_classified_as_required() -> None:
    decision = decide_rag_need("Nasıl?", detect_intents("Nasıl?"))

    assert decision.status == RAGNeedStatus.UNRESOLVED


def test_rag_decision_is_repeatable() -> None:
    resolution = resolve_intents((IntentType.STUDY_ADVICE,))

    assert decide_rag_need("request", resolution) == decide_rag_need(
        "request", resolution
    )


def test_intent_input_order_does_not_change_decision() -> None:
    forward = IntentResolution(
        IntentResolutionStatus.RESOLVED,
        (IntentType.STUDY_ADVICE, IntentType.PLANNING),
    )
    reverse = IntentResolution(
        IntentResolutionStatus.RESOLVED,
        (IntentType.PLANNING, IntentType.STUDY_ADVICE),
    )

    assert decide_rag_need("request", forward) == decide_rag_need(
        "request", reverse
    )


def test_rag_decision_is_immutable() -> None:
    decision = decide_rag_need(
        "request", resolve_intents((IntentType.GENERAL_CONVERSATION,))
    )

    with pytest.raises(FrozenInstanceError):
        decision.status = RAGNeedStatus.REQUIRED


@pytest.mark.parametrize(
    "factory",
    [
        lambda: RAGNeedDecision(
            RAGNeedStatus.REQUIRED,
            (IntentType.STUDY_ADVICE, IntentType.STUDY_ADVICE),
            RAGNeedSource.REQUIRED_INTENT,
        ),
        lambda: RAGNeedDecision(
            RAGNeedStatus.REQUIRED,
            (IntentType.STUDY_ADVICE, IntentType.PLANNING),
            RAGNeedSource.REQUIRED_INTENT,
        ),
        lambda: RAGNeedDecision(
            RAGNeedStatus.REQUIRED,
            (IntentType.PLANNING,),
            RAGNeedSource.REQUIRED_INTENT,
        ),
        lambda: RAGNeedDecision(
            RAGNeedStatus.NOT_REQUIRED,
            (IntentType.STUDY_ADVICE,),
            RAGNeedSource.LOCAL_INTENT,
        ),
        lambda: RAGNeedDecision(
            RAGNeedStatus.UNRESOLVED,
            (IntentType.PLANNING,),
            RAGNeedSource.UNRESOLVED,
        ),
    ],
)
def test_invalid_direct_decision_state_is_rejected(factory) -> None:
    with pytest.raises(ValueError):
        factory()


def test_plan_adjustment_source_rejects_resolved_planning_intent() -> None:
    with pytest.raises(ValueError, match="requires no resolved intents"):
        RAGNeedDecision(
            RAGNeedStatus.NOT_REQUIRED,
            (IntentType.PLANNING,),
            RAGNeedSource.PLAN_ADJUSTMENT_SIGNAL,
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
        description="Continue studying",
    )


def make_snapshot(
    learner: Learner,
    contexts: tuple[LearningContext, ...],
    *,
    goals: tuple[Goal, ...] = (),
) -> LearnerMemorySnapshot:
    return LearnerMemorySnapshot(
        learner=learner,
        contexts=contexts,
        goals=goals,
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


def make_registry(
    *contexts_and_phrases: tuple[LearningContext, str],
) -> SpecialtyProfileRegistry:
    registry = SpecialtyProfileRegistry()
    for context, phrase in contexts_and_phrases:
        registry.register(
            SpecialtyProfile(
                profile_code=context.program_code,
                profile_family=context.context_type,
                display_name=context.program_code,
                profile_version=1,
                terminology={
                    "context_routing": {"explicit_phrases": [phrase]}
                },
            )
        )
    return registry


class RecordingRetriever:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, str | set[str]] | None]] = []

    def search(
        self,
        query: str,
        limit: int = 3,
        filters: dict[str, str | set[str]] | None = None,
    ) -> list[object]:
        self.calls.append((query, filters))
        return []


def make_runtime(
    snapshot: LearnerMemorySnapshot,
    *,
    registry: SpecialtyProfileRegistry | None = None,
    retriever: RecordingRetriever | None = None,
) -> tuple[CoachOrchestrator, RecordingRetriever | None, FakeLLMProvider]:
    memory = Mock(spec=LearnerMemoryService)
    memory.get_learner_memory_snapshot.return_value = snapshot
    provider = FakeLLMProvider(
        responder=lambda request: (
            '{"response_text":"Birlikte inceleyelim.","proposal":null}'
            if "ONLY valid JSON object" in request.system_prompt
            else "Birlikte inceleyelim."
        )
    )
    orchestrator = CoachOrchestrator(
        memory,
        provider,
        retriever,
        specialty_registry=registry,
    )
    return orchestrator, retriever, provider


@pytest.mark.parametrize(
    "message",
    [
        "Merhaba",
        "Beni motive eder misin?",
        "Bana haftalık çalışma planı hazırla.",
        "74 net yaptım.",
        "Bugün 3 saatim var, programımı 3 saate indir.",
    ],
)
def test_runtime_not_required_messages_skip_retriever(message: str) -> None:
    learner = Learner()
    context = make_context(learner, "program", ContextType.OTHER)
    retriever = RecordingRetriever()
    orchestrator, _, provider = make_runtime(
        make_snapshot(learner, (context,)), retriever=retriever
    )

    orchestrator.respond(learner.learner_id, message)

    assert retriever.calls == []
    assert len(provider.requests) == 1


@pytest.mark.parametrize(
    "message",
    [
        "Aralıklı tekrar nedir?",
        "Matematiğe nasıl çalışmalıyım?",
        "Bana yardımcı olur musun?",
        "Bu konuya başlamadan önce hangi konuları bilmeliyim?",
    ],
)
def test_runtime_required_and_unresolved_messages_call_retriever(
    message: str,
) -> None:
    learner = Learner()
    context = make_context(learner, "program", ContextType.OTHER)
    retriever = RecordingRetriever()
    orchestrator, _, _ = make_runtime(
        make_snapshot(learner, (context,)), retriever=retriever
    )

    orchestrator.respond(learner.learner_id, message)

    assert retriever.calls == [(message, {"program": {"global", "program"}})]


def test_runtime_selected_context_scope_excludes_other_active_program() -> None:
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
    registry = make_registry((school, "school signal"), (exam, "exam signal"))
    retriever = RecordingRetriever()
    orchestrator, _, _ = make_runtime(
        make_snapshot(learner, (school, exam)),
        registry=registry,
        retriever=retriever,
    )
    message = "exam signal. Aralıklı tekrar nasıl yapılır?"

    orchestrator.respond(learner.learner_id, message)

    assert retriever.calls == [
        (message, {"program": {"global", "exam_program"}})
    ]
    assert "school_program" not in retriever.calls[0][1]["program"]


def test_runtime_memory_context_routing_still_controls_rag_scope() -> None:
    learner = Learner()
    first = make_context(learner, "first_program", ContextType.OTHER)
    second = make_context(learner, "second_program", ContextType.OTHER)
    registry = make_registry((first, "first signal"), (second, "second signal"))
    retriever = RecordingRetriever()
    orchestrator, _, _ = make_runtime(
        make_snapshot(
            learner,
            (first, second),
            goals=(make_goal(learner, second),),
        ),
        registry=registry,
        retriever=retriever,
    )
    message = "Aralıklı tekrar nasıl yapılır?"

    orchestrator.respond(learner.learner_id, message)

    assert retriever.calls == [
        (message, {"program": {"global", "second_program"}})
    ]


def test_runtime_zero_active_required_request_uses_global_only_scope() -> None:
    learner = Learner()
    completed = make_context(
        learner,
        "past_program",
        ContextType.OTHER,
        status=ContextStatus.COMPLETED,
    )
    retriever = RecordingRetriever()
    orchestrator, _, _ = make_runtime(
        make_snapshot(learner, (completed,)), retriever=retriever
    )
    message = "Aralıklı tekrar nedir?"

    orchestrator.respond(learner.learner_id, message)

    assert retriever.calls == [(message, {"program": {"global"}})]


def test_not_required_request_still_calls_validator(monkeypatch) -> None:
    learner = Learner()
    context = make_context(learner, "program", ContextType.OTHER)
    validator = Mock(side_effect=lambda text, **_: text)
    monkeypatch.setattr(coach_module, "validate_response", validator)
    retriever = RecordingRetriever()
    orchestrator, _, provider = make_runtime(
        make_snapshot(learner, (context,)), retriever=retriever
    )

    result = orchestrator.respond(learner.learner_id, "Merhaba")

    assert result.text == "Birlikte inceleyelim."
    assert len(provider.requests) == 1
    validator.assert_called_once()


def test_ambiguous_context_stops_before_intent_rag_llm_and_validator(
    monkeypatch,
) -> None:
    learner = Learner()
    first = make_context(learner, "first_program", ContextType.OTHER)
    second = make_context(learner, "second_program", ContextType.OTHER)
    registry = make_registry((first, "first signal"), (second, "second signal"))
    retriever = RecordingRetriever()
    orchestrator, _, provider = make_runtime(
        make_snapshot(learner, (first, second)),
        registry=registry,
        retriever=retriever,
    )
    monkeypatch.setattr(
        coach_module,
        "detect_intents",
        lambda *_: pytest.fail("intent detection must not be called"),
    )
    monkeypatch.setattr(
        coach_module,
        "validate_response",
        lambda *_args, **_kwargs: pytest.fail("validator must not be called"),
    )

    result = orchestrator.respond(learner.learner_id, "ambiguous request")

    assert result.model == "deterministic"
    assert retriever.calls == []
    assert provider.requests == []


def test_explicit_context_behavior_and_scope_are_unchanged() -> None:
    learner = Learner()
    first = make_context(learner, "first_program", ContextType.OTHER)
    second = make_context(learner, "second_program", ContextType.OTHER)
    registry = make_registry((first, "first signal"), (second, "second signal"))
    retriever = RecordingRetriever()
    orchestrator, _, _ = make_runtime(
        make_snapshot(learner, (first, second)),
        registry=registry,
        retriever=retriever,
    )
    message = "second signal. Aralıklı tekrar nasıl yapılır?"

    orchestrator.respond(
        learner.learner_id,
        message,
        context_id=first.context_id,
    )

    assert retriever.calls == [
        (message, {"program": {"global", "first_program"}})
    ]


def test_invalid_explicit_context_stops_before_intent_detection(monkeypatch) -> None:
    learner = Learner()
    context = make_context(learner, "program", ContextType.OTHER)
    retriever = RecordingRetriever()
    orchestrator, _, provider = make_runtime(
        make_snapshot(learner, (context,)), retriever=retriever
    )
    monkeypatch.setattr(
        coach_module,
        "detect_intents",
        lambda *_: pytest.fail("intent detection must not be called"),
    )

    with pytest.raises(ValueError, match="requested context"):
        orchestrator.respond(learner.learner_id, "request", context_id=uuid4())

    assert retriever.calls == []
    assert provider.requests == []


def test_retriever_none_does_not_break_required_request() -> None:
    learner = Learner()
    context = make_context(learner, "program", ContextType.OTHER)
    orchestrator, _, provider = make_runtime(make_snapshot(learner, (context,)))

    result = orchestrator.respond(learner.learner_id, "Aralıklı tekrar nedir?")

    assert result.text == "Birlikte inceleyelim."
    assert len(provider.requests) == 1


def test_intent_detector_runs_once_after_context_routing(monkeypatch) -> None:
    learner = Learner()
    context = make_context(learner, "program", ContextType.OTHER)
    orchestrator, _, _ = make_runtime(make_snapshot(learner, (context,)))
    original = coach_module.detect_intents
    detector = Mock(side_effect=original)
    monkeypatch.setattr(coach_module, "detect_intents", detector)

    orchestrator.respond(learner.learner_id, "Merhaba")

    detector.assert_called_once_with("Merhaba")
