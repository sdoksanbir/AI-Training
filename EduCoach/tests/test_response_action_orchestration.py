import inspect
import json
from unittest.mock import Mock
from uuid import uuid4

import pytest

import educoach.orchestrator.coach as coach_module
from educoach.llm import FakeLLMProvider
from educoach.models import ContextType, Learner, LearningContext
from educoach.orchestrator import (
    CoachOrchestrator,
    ResponseAutoFixRequired,
    ResponseRegenerationExhausted,
    ResponseRegenerationRequired,
    handle_response_validation_action,
)
from educoach.rules import RuleSeverity, RuleViolation
from educoach.services import LearnerMemoryService, LearnerMemorySnapshot
from educoach.validators import (
    ResponseValidationAction,
    ResponseValidationError,
    ResponseValidationReport,
    evaluate_response,
)


def violation(rule_id: str) -> RuleViolation:
    return RuleViolation(
        rule_id=rule_id,
        severity=RuleSeverity.ERROR,
        message=rule_id,
    )


def report(
    action: ResponseValidationAction,
    *rule_ids: str,
) -> ResponseValidationReport:
    return ResponseValidationReport(
        action=action,
        violations=tuple(violation(rule_id) for rule_id in rule_ids),
    )


def test_pass_returns_stripped_text() -> None:
    assert handle_response_validation_action(
        "  Hazırım.  ", report(ResponseValidationAction.PASS)
    ) == "Hazırım."


def test_action_handler_has_no_provider_or_retry_dependency() -> None:
    parameters = inspect.signature(handle_response_validation_action).parameters

    assert tuple(parameters) == ("text", "report")


def test_block_raises_compatible_error_with_report_and_violation_order() -> None:
    validation_report = report(
        ResponseValidationAction.BLOCK,
        "first",
        "second",
    )

    with pytest.raises(ResponseValidationError) as captured:
        handle_response_validation_action("blocked", validation_report)

    assert type(captured.value) is ResponseValidationError
    assert captured.value.report is validation_report
    assert captured.value.violations == ["first", "second"]


def test_regenerate_raises_typed_compatible_boundary() -> None:
    validation_report = report(
        ResponseValidationAction.REGENERATE,
        "first",
        "second",
    )

    with pytest.raises(ResponseRegenerationRequired) as captured:
        handle_response_validation_action("unchanged", validation_report)

    assert isinstance(captured.value, ResponseValidationError)
    assert captured.value.report is validation_report
    assert captured.value.violations == ["first", "second"]
    assert captured.value.report.action is ResponseValidationAction.REGENERATE


def test_auto_fix_raises_typed_compatible_boundary() -> None:
    validation_report = report(
        ResponseValidationAction.AUTO_FIX,
        "first",
        "second",
    )

    with pytest.raises(ResponseAutoFixRequired) as captured:
        handle_response_validation_action("unchanged", validation_report)

    assert isinstance(captured.value, ResponseValidationError)
    assert captured.value.report is validation_report
    assert captured.value.violations == ["first", "second"]
    assert captured.value.report.action is ResponseValidationAction.AUTO_FIX


@pytest.mark.parametrize(
    "wrong_action",
    [
        ResponseValidationAction.PASS,
        ResponseValidationAction.AUTO_FIX,
        ResponseValidationAction.BLOCK,
    ],
)
def test_regeneration_exception_rejects_wrong_report(
    wrong_action: ResponseValidationAction,
) -> None:
    with pytest.raises(ValueError, match="must be regenerate"):
        ResponseRegenerationRequired(report(wrong_action))


@pytest.mark.parametrize(
    "wrong_action",
    [
        ResponseValidationAction.PASS,
        ResponseValidationAction.REGENERATE,
        ResponseValidationAction.BLOCK,
    ],
)
def test_auto_fix_exception_rejects_wrong_report(
    wrong_action: ResponseValidationAction,
) -> None:
    with pytest.raises(ValueError, match="must be auto_fix"):
        ResponseAutoFixRequired(report(wrong_action))


@pytest.mark.parametrize(
    ("action", "error_type"),
    [
        (ResponseValidationAction.BLOCK, ResponseValidationError),
        (ResponseValidationAction.REGENERATE, ResponseRegenerationRequired),
        (ResponseValidationAction.AUTO_FIX, ResponseAutoFixRequired),
    ],
)
def test_non_pass_actions_do_not_mutate_input_text(
    action: ResponseValidationAction,
    error_type: type[ResponseValidationError],
) -> None:
    text = "  original response  "

    with pytest.raises(error_type):
        handle_response_validation_action(text, report(action, "violation"))

    assert text == "  original response  "


def test_unexpected_action_fails_closed() -> None:
    validation_report = report(ResponseValidationAction.PASS)
    object.__setattr__(validation_report, "action", "unexpected")

    with pytest.raises(RuntimeError, match="Unsupported response validation action"):
        handle_response_validation_action("text", validation_report)


def test_current_evaluator_does_not_manufacture_auto_fix() -> None:
    assert evaluate_response("Hazırım.").action is ResponseValidationAction.PASS


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


def make_runtime(
    response_text: str,
    *,
    retriever=None,
) -> tuple[CoachOrchestrator, Mock, FakeLLMProvider, Learner]:
    learner = Learner()
    contexts = (make_context(learner),)
    memory = Mock(spec=LearnerMemoryService)
    memory.get_learner_memory_snapshot.return_value = make_snapshot(
        learner, contexts
    )
    provider = FakeLLMProvider(responder=lambda _: response_text)
    return CoachOrchestrator(memory, provider, retriever), memory, provider, learner


def structured_response(response_text: str = "Planın hazır.") -> str:
    return json.dumps(
        {
            "response_text": response_text,
            "proposal": {
                "title": "Haftalık plan",
                "plan_type": "weekly",
                "start_date": "2026-10-05",
                "end_date": "2026-10-05",
                "tasks": [
                    {
                        "task_date": "2026-10-05",
                        "task_type": "study",
                        "description": "Matematik çalış",
                        "planned_minutes": 60,
                    }
                ],
            },
        },
        ensure_ascii=False,
    )


def test_runtime_pass_returns_stripped_result_with_one_provider_call() -> None:
    orchestrator, _, provider, learner = make_runtime("  Hazırım.  ")

    result = orchestrator.respond(learner.learner_id, "Merhaba")

    assert result.text == "Hazırım."
    assert len(provider.requests) == 1


def test_runtime_regenerate_exhausts_after_one_retry() -> None:
    orchestrator, _, provider, learner = make_runtime("Sen 10. sınıftasın.")

    with pytest.raises(ResponseRegenerationExhausted) as captured:
        orchestrator.respond(learner.learner_id, "Sınıfımı değerlendir")

    assert captured.value.report.action is ResponseValidationAction.REGENERATE
    assert captured.value.violations == ["CORE_MEMORY_CONTRADICTION"]
    assert len(provider.requests) == 2


def test_runtime_block_is_not_converted_to_regeneration() -> None:
    orchestrator, _, provider, learner = make_runtime(
        "Kaynak: https://example.com"
    )

    with pytest.raises(ResponseValidationError) as captured:
        orchestrator.respond(learner.learner_id, "Kaynak ver")

    assert not isinstance(captured.value, ResponseRegenerationRequired)
    assert captured.value.report.action is ResponseValidationAction.BLOCK
    assert len(provider.requests) == 1


def test_structured_planning_pass_returns_proposal() -> None:
    orchestrator, memory, provider, learner = make_runtime(structured_response())

    result = orchestrator.respond(learner.learner_id, "Bana haftalık plan yap")

    assert result.text == "Planın hazır."
    assert result.study_plan_proposal is not None
    assert len(provider.requests) == 1
    memory.save_study_plan.assert_not_called()


def test_structured_planning_regenerate_exhausts_without_persistence() -> None:
    orchestrator, memory, provider, learner = make_runtime(
        structured_response("Sen 10. sınıftasın.")
    )

    with pytest.raises(ResponseRegenerationExhausted):
        orchestrator.respond(learner.learner_id, "Bana haftalık plan yap")

    assert len(provider.requests) == 2
    memory.save_study_plan.assert_not_called()


def test_structured_planning_block_returns_no_result_or_persistence() -> None:
    orchestrator, memory, provider, learner = make_runtime(
        structured_response("Kaynak: https://example.com")
    )

    with pytest.raises(ResponseValidationError) as captured:
        orchestrator.respond(learner.learner_id, "Bana haftalık plan yap")

    assert captured.value.report.action is ResponseValidationAction.BLOCK
    assert len(provider.requests) == 1
    memory.save_study_plan.assert_not_called()


def test_runtime_evaluates_response_text_instead_of_raw_structured_json(
    monkeypatch,
) -> None:
    raw = structured_response("Gösterilecek cevap.")
    orchestrator, _, _, learner = make_runtime(raw)
    evaluator = Mock(
        return_value=ResponseValidationReport(ResponseValidationAction.PASS)
    )
    monkeypatch.setattr(coach_module, "evaluate_response", evaluator)

    result = orchestrator.respond(learner.learner_id, "Bana haftalık plan yap")

    assert result.text == "Gösterilecek cevap."
    assert evaluator.call_args.args[0] == "Gösterilecek cevap."
    assert evaluator.call_args.args[0] != raw


def test_ambiguous_context_stops_before_evaluator_and_provider(monkeypatch) -> None:
    learner = Learner()
    contexts = (
        make_context(learner, "school_11"),
        make_context(learner, "school_12"),
    )
    memory = Mock(spec=LearnerMemoryService)
    memory.get_learner_memory_snapshot.return_value = make_snapshot(
        learner, contexts
    )
    provider = FakeLLMProvider()
    orchestrator = CoachOrchestrator(memory, provider)
    monkeypatch.setattr(
        coach_module,
        "evaluate_response",
        lambda *_args, **_kwargs: pytest.fail("evaluator must not be called"),
    )

    result = orchestrator.respond(learner.learner_id, "Genel bir isteğim var")

    assert result.model == "deterministic"
    assert provider.requests == []


def test_invalid_explicit_context_stops_before_evaluator_and_provider(
    monkeypatch,
) -> None:
    orchestrator, _, provider, learner = make_runtime("unused")
    monkeypatch.setattr(
        coach_module,
        "evaluate_response",
        lambda *_args, **_kwargs: pytest.fail("evaluator must not be called"),
    )

    with pytest.raises(ValueError, match="requested context"):
        orchestrator.respond(
            learner.learner_id,
            "Merhaba",
            context_id=uuid4(),
        )

    assert provider.requests == []


class RecordingRetriever:
    def __init__(self) -> None:
        self.filters: list[dict[str, str | set[str]] | None] = []

    def search(self, query, limit=3, filters=None):
        self.filters.append(filters)
        return []


def test_rag_gating_and_selected_context_scope_are_unchanged() -> None:
    retriever = RecordingRetriever()
    orchestrator, _, provider, learner = make_runtime(
        "Aralıklı tekrar faydalıdır.",
        retriever=retriever,
    )

    result = orchestrator.respond(
        learner.learner_id,
        "Aralıklı tekrar nasıl yapılır?",
    )

    assert result.text == "Aralıklı tekrar faydalıdır."
    assert retriever.filters == [{"program": {"global", "school_11"}}]
    assert len(provider.requests) == 1


def test_non_planning_request_keeps_plain_text_flow() -> None:
    orchestrator, _, provider, learner = make_runtime("Düz metin cevap.")

    result = orchestrator.respond(learner.learner_id, "Merhaba")

    assert result.text == "Düz metin cevap."
    assert result.study_plan_proposal is None
    assert "ONLY valid JSON object" not in provider.requests[0].system_prompt
