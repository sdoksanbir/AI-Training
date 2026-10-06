import json
from unittest.mock import Mock
from uuid import uuid4

import pytest

import educoach.orchestrator.coach as coach_module
from educoach.llm import LLMProvider, LLMRequest, LLMResponse
from educoach.models import ContextType, Learner, LearningContext
from educoach.orchestrator import (
    MAX_REGENERATION_ATTEMPTS,
    CoachOrchestrator,
    ResponseAutoFixRequired,
    ResponseRegenerationExhausted,
    ResponseRegenerationRequired,
    StructuredLLMOutputError,
    build_regeneration_request,
)
from educoach.rules import RuleSeverity, RuleViolation
from educoach.services import LearnerMemoryService, LearnerMemorySnapshot
from educoach.validators import (
    ResponseValidationAction,
    ResponseValidationError,
    ResponseValidationReport,
)


class SequencedProvider(LLMProvider):
    def __init__(self, outcomes: list[LLMResponse | Exception]) -> None:
        self.outcomes = outcomes
        self.requests: list[LLMRequest] = []

    def health(self) -> bool:
        return True

    def generate(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        outcome = self.outcomes[len(self.requests) - 1]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class RecordingRetriever:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, str | set[str]] | None]] = []

    def search(self, query, limit=3, filters=None):
        self.calls.append((query, filters))
        return []


def validation_report(
    action: ResponseValidationAction,
    *violations: RuleViolation,
) -> ResponseValidationReport:
    return ResponseValidationReport(action=action, violations=violations)


def violation(rule_id: str, message: str | None = None) -> RuleViolation:
    return RuleViolation(
        rule_id=rule_id,
        severity=RuleSeverity.ERROR,
        message=message or f"Message for {rule_id}",
    )


def make_context(
    learner: Learner,
    program_code: str = "school_11",
) -> LearningContext:
    return LearningContext(
        learner_id=learner.learner_id,
        context_type=ContextType.SCHOOL,
        program_code=program_code,
        grade_level=11,
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


def make_runtime(
    outcomes: list[LLMResponse | Exception],
    *,
    retriever=None,
) -> tuple[CoachOrchestrator, Mock, SequencedProvider, Learner]:
    learner = Learner()
    context = make_context(learner)
    memory = Mock(spec=LearnerMemoryService)
    memory.get_learner_memory_snapshot.return_value = make_snapshot(
        learner, (context,)
    )
    provider = SequencedProvider(outcomes)
    orchestrator = CoachOrchestrator(memory, provider, retriever)
    return orchestrator, memory, provider, learner


def response(text: str, model: str = "model") -> LLMResponse:
    return LLMResponse(text=text, model=model)


def structured_response(
    response_text: str,
    *,
    title: str,
    description: str,
) -> str:
    return json.dumps(
        {
            "response_text": response_text,
            "proposal": {
                "title": title,
                "plan_type": "weekly",
                "start_date": "2026-10-05",
                "end_date": "2026-10-05",
                "tasks": [
                    {
                        "task_date": "2026-10-05",
                        "task_type": "study",
                        "description": description,
                        "planned_minutes": 60,
                    }
                ],
            },
        },
        ensure_ascii=False,
    )


def test_regeneration_policy_is_exactly_one_attempt() -> None:
    assert MAX_REGENERATION_ATTEMPTS == 1


def test_regeneration_request_reuses_request_and_adds_authoritative_feedback() -> None:
    original = LLMRequest(
        system_prompt="ORIGINAL SYSTEM",
        user_message="original user message",
        memory_context="original memory and RAG context",
    )
    report = validation_report(
        ResponseValidationAction.REGENERATE,
        violation("FIRST_RULE", "First authoritative message"),
        violation("SECOND_RULE", "Second authoritative message"),
    )

    retry = build_regeneration_request(original, report)

    assert retry.user_message == original.user_message
    assert retry.memory_context == original.memory_context
    assert retry.system_prompt.startswith(original.system_prompt)
    assert "FIRST_RULE: First authoritative message" in retry.system_prompt
    assert "SECOND_RULE: Second authoritative message" in retry.system_prompt
    assert retry.system_prompt.index("FIRST_RULE") < retry.system_prompt.index(
        "SECOND_RULE"
    )
    assert "SECRET RAW REJECTED RESPONSE" not in retry.system_prompt
    assert "Do not mention validator internals" in retry.system_prompt
    assert "Preserve every original system instruction" in retry.system_prompt


@pytest.mark.parametrize(
    "action",
    [
        ResponseValidationAction.PASS,
        ResponseValidationAction.AUTO_FIX,
        ResponseValidationAction.BLOCK,
    ],
)
def test_regeneration_request_requires_regenerate_report(
    action: ResponseValidationAction,
) -> None:
    with pytest.raises(ValueError, match="must be regenerate"):
        build_regeneration_request(
            LLMRequest(system_prompt="system", user_message="user"),
            validation_report(action),
        )


def test_exhausted_boundary_preserves_hierarchy_report_and_order() -> None:
    final_report = validation_report(
        ResponseValidationAction.REGENERATE,
        violation("first"),
        violation("second"),
    )

    exhausted = ResponseRegenerationExhausted(final_report)

    assert isinstance(exhausted, ResponseRegenerationRequired)
    assert isinstance(exhausted, ResponseValidationError)
    assert exhausted.report is final_report
    assert exhausted.violations == ["first", "second"]


def test_exhausted_boundary_rejects_non_regenerate_report() -> None:
    with pytest.raises(ValueError, match="must be regenerate"):
        ResponseRegenerationExhausted(
            validation_report(ResponseValidationAction.BLOCK)
        )


def test_first_pass_uses_one_provider_call() -> None:
    orchestrator, _, provider, learner = make_runtime(
        [response("  Geçerli cevap.  ", "first-model")]
    )

    result = orchestrator.respond(learner.learner_id, "Merhaba")

    assert result.text == "Geçerli cevap."
    assert result.model == "first-model"
    assert len(provider.requests) == 1
    prompt = provider.requests[0].system_prompt.lower()
    assert "harici url" in prompt
    assert "web adresi" in prompt
    assert "www" in prompt


def test_first_block_uses_one_provider_call() -> None:
    orchestrator, _, provider, learner = make_runtime(
        [response("x" * 12001)]
    )

    with pytest.raises(ResponseValidationError) as captured:
        orchestrator.respond(learner.learner_id, "Uzun cevap ver")

    assert not isinstance(captured.value, ResponseRegenerationRequired)
    assert captured.value.report.action is ResponseValidationAction.BLOCK
    assert len(provider.requests) == 1


def test_first_auto_fix_uses_one_provider_call(monkeypatch) -> None:
    auto_fix_report = validation_report(
        ResponseValidationAction.AUTO_FIX,
        violation("AUTO_FIX_RULE"),
    )
    monkeypatch.setattr(
        coach_module,
        "evaluate_response",
        Mock(return_value=auto_fix_report),
    )
    orchestrator, _, provider, learner = make_runtime([response("candidate")])

    with pytest.raises(ResponseAutoFixRequired):
        orchestrator.respond(learner.learner_id, "Merhaba")

    assert len(provider.requests) == 1


def test_plain_regeneration_success_returns_second_text_and_model() -> None:
    orchestrator, _, provider, learner = make_runtime(
        [
            response("Sen 10. sınıftasın.", "first-model"),
            response("Kayıtlarına göre 11. sınıftasın.", "second-model"),
        ]
    )

    result = orchestrator.respond(
        learner.learner_id,
        "Sınıf düzeyimi değerlendir",
    )

    assert result.text == "Kayıtlarına göre 11. sınıftasın."
    assert result.model == "second-model"
    assert len(provider.requests) == 2


def test_external_link_regenerates_once_and_returns_clean_response() -> None:
    rejected = "Kaynak: https://example.com SECRET RAW REJECTED RESPONSE"
    clean = "Doğrulanmamış dış bağlantı vermeden açıklayabilirim."
    orchestrator, _, provider, learner = make_runtime(
        [response(rejected, "first-model"), response(clean, "second-model")]
    )
    message = "Kaynak öner"

    result = orchestrator.respond(learner.learner_id, message)

    assert result.text == clean
    assert result.model == "second-model"
    assert "http://" not in result.text
    assert "https://" not in result.text
    assert "www." not in result.text
    assert "external_link_not_verified" not in result.text
    assert len(provider.requests) == 2
    first, retry = provider.requests
    assert retry.user_message == first.user_message == message
    assert retry.memory_context == first.memory_context
    assert retry.system_prompt.startswith(first.system_prompt)
    assert "external_link_not_verified" in retry.system_prompt
    assert rejected not in retry.system_prompt


def test_repeated_external_link_exhausts_after_two_calls() -> None:
    orchestrator, _, provider, learner = make_runtime(
        [
            response("Kaynak: https://example.com"),
            response("Kaynak: www.example.com"),
        ]
    )

    with pytest.raises(ResponseRegenerationExhausted) as captured:
        orchestrator.respond(learner.learner_id, "Kaynak öner")

    assert captured.value.report.action is ResponseValidationAction.REGENERATE
    assert captured.value.violations == ["external_link_not_verified"]
    assert len(provider.requests) == 2


def test_runtime_retry_reuses_user_message_memory_and_original_prompt() -> None:
    raw_rejected = "Sen 10. sınıftasın. SECRET RAW REJECTED RESPONSE"
    orchestrator, _, provider, learner = make_runtime(
        [response(raw_rejected), response("Düzeltilmiş cevap.")]
    )
    message = "Sınıf düzeyimi değerlendir"

    orchestrator.respond(learner.learner_id, message)

    first, retry = provider.requests
    assert retry.user_message == first.user_message == message
    assert retry.memory_context == first.memory_context
    assert retry.system_prompt.startswith(first.system_prompt)
    assert "CORE_MEMORY_CONTRADICTION" in retry.system_prompt
    assert "Response contradicts recorded learner memory" in retry.system_prompt
    assert raw_rejected not in retry.system_prompt
    assert "Do not mention validator internals" in retry.system_prompt


def test_second_regenerate_exhausts_without_third_call(monkeypatch) -> None:
    first_report = validation_report(
        ResponseValidationAction.REGENERATE,
        violation("FIRST_ATTEMPT"),
    )
    final_report = validation_report(
        ResponseValidationAction.REGENERATE,
        violation("FINAL_FIRST"),
        violation("FINAL_SECOND"),
    )
    evaluator = Mock(side_effect=[first_report, final_report])
    monkeypatch.setattr(coach_module, "evaluate_response", evaluator)
    orchestrator, _, provider, learner = make_runtime(
        [response("first"), response("second")]
    )

    with pytest.raises(ResponseRegenerationExhausted) as captured:
        orchestrator.respond(learner.learner_id, "Merhaba")

    assert captured.value.report is final_report
    assert captured.value.violations == ["FINAL_FIRST", "FINAL_SECOND"]
    assert len(provider.requests) == 2
    assert evaluator.call_count == 2


def test_second_block_remains_normal_block_error() -> None:
    orchestrator, _, provider, learner = make_runtime(
        [
            response("Sen 10. sınıftasın."),
            response("Kaynak: https://example.com" + "x" * 12001),
        ]
    )

    with pytest.raises(ResponseValidationError) as captured:
        orchestrator.respond(learner.learner_id, "Sınıfımı değerlendir")

    assert not isinstance(captured.value, ResponseRegenerationExhausted)
    assert captured.value.report.action is ResponseValidationAction.BLOCK
    assert len(provider.requests) == 2


def test_second_auto_fix_raises_without_third_call(monkeypatch) -> None:
    evaluator = Mock(
        side_effect=[
            validation_report(
                ResponseValidationAction.REGENERATE,
                violation("REGENERATE_RULE"),
            ),
            validation_report(
                ResponseValidationAction.AUTO_FIX,
                violation("AUTO_FIX_RULE"),
            ),
        ]
    )
    monkeypatch.setattr(coach_module, "evaluate_response", evaluator)
    orchestrator, _, provider, learner = make_runtime(
        [response("first"), response("second")]
    )

    with pytest.raises(ResponseAutoFixRequired) as captured:
        orchestrator.respond(learner.learner_id, "Merhaba")

    assert captured.value.report.action is ResponseValidationAction.AUTO_FIX
    assert len(provider.requests) == 2


def test_initial_provider_error_is_not_retried() -> None:
    provider_error = RuntimeError("provider unavailable")
    orchestrator, _, provider, learner = make_runtime([provider_error])

    with pytest.raises(RuntimeError, match="provider unavailable"):
        orchestrator.respond(learner.learner_id, "Merhaba")

    assert len(provider.requests) == 1


def test_regeneration_provider_error_is_not_retried_again() -> None:
    provider_error = RuntimeError("retry provider unavailable")
    orchestrator, _, provider, learner = make_runtime(
        [response("Sen 10. sınıftasın."), provider_error]
    )

    with pytest.raises(RuntimeError, match="retry provider unavailable"):
        orchestrator.respond(learner.learner_id, "Sınıfımı değerlendir")

    assert len(provider.requests) == 2


def test_regeneration_reuses_retrieval_snapshot_intent_and_context(monkeypatch) -> None:
    retriever = RecordingRetriever()
    original_context_router = coach_module.resolve_request_context
    original_intent_detector = coach_module.detect_intents
    original_rag_gate = coach_module.decide_rag_need
    context_router = Mock(side_effect=original_context_router)
    intent_detector = Mock(side_effect=original_intent_detector)
    rag_gate = Mock(side_effect=original_rag_gate)
    monkeypatch.setattr(coach_module, "resolve_request_context", context_router)
    monkeypatch.setattr(coach_module, "detect_intents", intent_detector)
    monkeypatch.setattr(coach_module, "decide_rag_need", rag_gate)
    orchestrator, memory, provider, learner = make_runtime(
        [
            response("Sen 10. sınıftasın."),
            response("Aralıklı tekrar için kısa aralıklarla çalışabilirsin."),
        ],
        retriever=retriever,
    )
    message = "Aralıklı tekrar nasıl yapılır?"

    orchestrator.respond(learner.learner_id, message)

    assert len(provider.requests) == 2
    assert retriever.calls == [
        (message, {"program": {"global", "school_11"}})
    ]
    assert memory.get_learner_memory_snapshot.call_count == 1
    assert context_router.call_count == 1
    assert intent_detector.call_count == 1
    assert rag_gate.call_count == 1


def test_ambiguous_context_still_uses_zero_provider_calls() -> None:
    learner = Learner()
    contexts = (
        make_context(learner, "school_11"),
        make_context(learner, "school_12"),
    )
    memory = Mock(spec=LearnerMemoryService)
    memory.get_learner_memory_snapshot.return_value = make_snapshot(
        learner, contexts
    )
    provider = SequencedProvider([])

    result = CoachOrchestrator(memory, provider).respond(
        learner.learner_id,
        "Genel bir isteğim var",
    )

    assert result.model == "deterministic"
    assert provider.requests == []


def test_invalid_explicit_context_still_uses_zero_provider_calls() -> None:
    orchestrator, _, provider, learner = make_runtime([])

    with pytest.raises(ValueError, match="requested context"):
        orchestrator.respond(
            learner.learner_id,
            "Merhaba",
            context_id=uuid4(),
        )

    assert provider.requests == []


def test_initial_malformed_structured_json_is_not_retried() -> None:
    orchestrator, memory, provider, learner = make_runtime(
        [response("not json")]
    )

    with pytest.raises(StructuredLLMOutputError):
        orchestrator.respond(learner.learner_id, "Bana haftalık plan yap")

    assert len(provider.requests) == 1
    memory.save_study_plan.assert_not_called()


def test_structured_regeneration_uses_only_second_proposal(monkeypatch) -> None:
    first = structured_response(
        "Sen 10. sınıftasın.",
        title="Rejected plan",
        description="Rejected task",
    )
    second = structured_response(
        "Kayıtlarına göre uygun plan hazır.",
        title="Accepted plan",
        description="Accepted task",
    )
    orchestrator, memory, provider, learner = make_runtime(
        [response(first, "first-model"), response(second, "second-model")]
    )
    original_materializer = coach_module.materialize_study_plan_write_proposal
    materialized = []

    def recording_materializer(*args, **kwargs):
        proposal = original_materializer(*args, **kwargs)
        materialized.append(proposal)
        return proposal

    monkeypatch.setattr(
        coach_module,
        "materialize_study_plan_write_proposal",
        recording_materializer,
    )

    result = orchestrator.respond(
        learner.learner_id,
        "Bana haftalık plan yap",
    )

    assert result.text == "Kayıtlarına göre uygun plan hazır."
    assert result.model == "second-model"
    assert result.study_plan_proposal is materialized[1]
    assert result.study_plan_proposal.plan.title == "Accepted plan"
    assert result.study_plan_proposal.tasks[0].description == "Accepted task"
    assert len(materialized) == 2
    assert materialized[0].plan.title == "Rejected plan"
    assert materialized[0].plan.plan_id != materialized[1].plan.plan_id
    assert materialized[0].tasks[0].task_id != materialized[1].tasks[0].task_id
    assert len(provider.requests) == 2
    retry_prompt = provider.requests[1].system_prompt
    assert "ONLY valid JSON object" in retry_prompt
    assert "learner_id" in retry_prompt
    assert "task_id" in retry_prompt
    memory.save_study_plan.assert_not_called()


def test_structured_retry_malformed_json_propagates_without_third_call() -> None:
    first = structured_response(
        "Sen 10. sınıftasın.",
        title="Rejected plan",
        description="Rejected task",
    )
    orchestrator, memory, provider, learner = make_runtime(
        [response(first), response("not json")]
    )

    with pytest.raises(StructuredLLMOutputError):
        orchestrator.respond(learner.learner_id, "Bana haftalık plan yap")

    assert len(provider.requests) == 2
    memory.save_study_plan.assert_not_called()


def test_structured_retry_block_returns_no_result_or_persistence() -> None:
    first = structured_response(
        "Sen 10. sınıftasın.",
        title="Rejected plan",
        description="Rejected task",
    )
    second = structured_response(
        "Kaynak: https://example.com" + "x" * 12001,
        title="Blocked plan",
        description="Blocked task",
    )
    orchestrator, memory, provider, learner = make_runtime(
        [response(first), response(second)]
    )

    with pytest.raises(ResponseValidationError) as captured:
        orchestrator.respond(learner.learner_id, "Bana haftalık plan yap")

    assert not isinstance(captured.value, ResponseRegenerationExhausted)
    assert captured.value.report.action is ResponseValidationAction.BLOCK
    assert len(provider.requests) == 2
    memory.save_study_plan.assert_not_called()


def test_structured_external_link_regenerates_to_clean_proposal() -> None:
    first = structured_response(
        "Kaynak: https://example.com",
        title="Rejected linked plan",
        description="Rejected linked task",
    )
    second = structured_response(
        "Bağlantısız plan hazır.",
        title="Accepted clean plan",
        description="Accepted clean task",
    )
    orchestrator, memory, provider, learner = make_runtime(
        [response(first), response(second)]
    )

    result = orchestrator.respond(learner.learner_id, "Bana haftalık plan yap")

    assert result.text == "Bağlantısız plan hazır."
    assert result.study_plan_proposal is not None
    assert result.study_plan_proposal.plan.title == "Accepted clean plan"
    assert len(provider.requests) == 2
    memory.save_study_plan.assert_not_called()


def test_structured_retry_regenerate_exhausts_without_persistence() -> None:
    first = structured_response(
        "Sen 10. sınıftasın.",
        title="First rejected plan",
        description="First rejected task",
    )
    second = structured_response(
        "Hâlâ 10. sınıftasın.",
        title="Second rejected plan",
        description="Second rejected task",
    )
    orchestrator, memory, provider, learner = make_runtime(
        [response(first), response(second)]
    )

    with pytest.raises(ResponseRegenerationExhausted):
        orchestrator.respond(learner.learner_id, "Bana haftalık plan yap")

    assert len(provider.requests) == 2
    memory.save_study_plan.assert_not_called()
