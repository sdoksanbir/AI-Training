from dataclasses import replace
from datetime import date
import json
from unittest.mock import Mock

import pytest

import educoach.orchestrator.coach as coach_module
from educoach.llm import LLMProvider, LLMRequest, LLMResponse
from educoach.models import (
    Availability,
    AvailabilityType,
    ContextType,
    DayOfWeek,
    Learner,
    LearningContext,
)
from educoach.orchestrator import (
    SUPPORTED_AUTO_FIX_RULE_IDS,
    CoachOrchestrator,
    ResponseAutoFixRequired,
    ResponseRegenerationExhausted,
    apply_response_auto_fix,
)
from educoach.rules import RuleSeverity, RuleViolation
from educoach.services import LearnerMemoryService, LearnerMemorySnapshot
from educoach.validators import (
    ResponseValidationAction,
    ResponseValidationError,
    ResponseValidationReport,
    evaluate_response,
    validate_response,
)
from educoach.validators.repetition import repetition_duplicate_segment_indexes


REPEATED_SEGMENT = "Matematik yanlışlarını dikkatle analiz et."


class SequencedProvider(LLMProvider):
    def __init__(self, responses: list[LLMResponse]) -> None:
        self.responses = responses
        self.requests: list[LLMRequest] = []

    def health(self) -> bool:
        return True

    def generate(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        return self.responses[len(self.requests) - 1]


class RecordingRetriever:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, str | set[str]] | None]] = []

    def search(self, query, limit=3, filters=None):
        self.calls.append((query, filters))
        return []


def violation(rule_id: str) -> RuleViolation:
    return RuleViolation(
        rule_id=rule_id,
        severity=RuleSeverity.ERROR,
        message=f"Message for {rule_id}",
    )


def report(
    action: ResponseValidationAction,
    *rule_ids: str,
) -> ResponseValidationReport:
    return ResponseValidationReport(
        action=action,
        violations=tuple(violation(rule_id) for rule_id in rule_ids),
    )


def repeated_text(count: int = 3, *, suffix: str = "Sonra soru çöz.") -> str:
    repeated = "\n".join(REPEATED_SEGMENT for _ in range(count))
    return repeated + (f"\n{suffix}" if suffix else "")


def make_snapshot(*, availability_minutes: int | None = None):
    learner = Learner()
    context = LearningContext(
        learner_id=learner.learner_id,
        context_type=ContextType.SCHOOL,
        program_code="school_11",
        grade_level=11,
    )
    snapshot = LearnerMemorySnapshot(
        learner=learner,
        contexts=(context,),
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
    if availability_minutes is not None:
        target_date = date(2026, 10, 5)
        availability = Availability(
            learner_id=learner.learner_id,
            day_of_week=DayOfWeek(target_date.weekday()),
            availability_type=AvailabilityType.AVAILABLE,
            available_minutes=availability_minutes,
            effective_from=target_date,
            effective_until=target_date,
        )
        snapshot = replace(snapshot, availability=(availability,))
    return learner, context, snapshot


def make_runtime(
    response_texts: list[str],
    *,
    retriever=None,
) -> tuple[CoachOrchestrator, Mock, SequencedProvider, Learner]:
    learner, _, snapshot = make_snapshot()
    memory = Mock(spec=LearnerMemoryService)
    memory.get_learner_memory_snapshot.return_value = snapshot
    provider = SequencedProvider(
        [
            LLMResponse(text=text, model=f"model-{index}")
            for index, text in enumerate(response_texts, start=1)
        ]
    )
    return CoachOrchestrator(memory, provider, retriever), memory, provider, learner


def structured_response(response_text: str) -> str:
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


def test_supported_auto_fix_policy_is_repetition_only() -> None:
    assert SUPPORTED_AUTO_FIX_RULE_IDS == frozenset(
        {"OUTPUT_REPETITION_LOOP"}
    )


def test_repetition_only_is_classified_as_auto_fix() -> None:
    validation = evaluate_response(repeated_text())

    assert validation.action is ResponseValidationAction.AUTO_FIX
    assert [item.rule_id for item in validation.violations] == [
        "OUTPUT_REPETITION_LOOP"
    ]


def test_repetition_and_guarantee_are_classified_as_regenerate() -> None:
    validation = evaluate_response(
        repeated_text(suffix="Bu programla kesin başarırsın.")
    )

    assert validation.action is ResponseValidationAction.REGENERATE
    assert [item.rule_id for item in validation.violations] == [
        "OUTPUT_REPETITION_LOOP",
        "OUTPUT_UNSUPPORTED_GUARANTEE",
    ]


def test_repetition_and_external_link_are_classified_as_regenerate() -> None:
    validation = evaluate_response(
        repeated_text(suffix="Kaynak: https://example.com")
    )

    assert validation.action is ResponseValidationAction.REGENERATE
    assert [item.rule_id for item in validation.violations] == [
        "external_link_not_verified",
        "OUTPUT_REPETITION_LOOP",
    ]


def test_plan_budget_only_remains_regenerate() -> None:
    _, _, snapshot = make_snapshot(availability_minutes=90)
    validation = evaluate_response(
        "2026-10-05 için:\n- Matematik: 60 dakika\n- Fizik: 45 dakika",
        snapshot=snapshot,
    )

    assert validation.action is ResponseValidationAction.REGENERATE
    assert [item.rule_id for item in validation.violations] == [
        "PLAN_AVAILABLE_TIME_LIMIT"
    ]


def test_repetition_and_plan_budget_are_classified_as_regenerate() -> None:
    _, _, snapshot = make_snapshot(availability_minutes=90)
    validation = evaluate_response(
        "2026-10-05 için:\n- Matematik: 60 dakika\n- Fizik: 45 dakika\n"
        + repeated_text(suffix=""),
        snapshot=snapshot,
    )

    assert validation.action is ResponseValidationAction.REGENERATE
    assert [item.rule_id for item in validation.violations] == [
        "PLAN_AVAILABLE_TIME_LIMIT",
        "OUTPUT_REPETITION_LOOP",
    ]


def test_unsupported_guarantee_only_remains_regenerate() -> None:
    validation = evaluate_response("Bu programla kesin başarırsın.")

    assert validation.action is ResponseValidationAction.REGENERATE
    assert [item.rule_id for item in validation.violations] == [
        "OUTPUT_UNSUPPORTED_GUARANTEE"
    ]


@pytest.mark.parametrize("count", [3, 4])
def test_consecutive_repetition_run_collapses_to_one(count: int) -> None:
    text = repeated_text(count)

    fixed = apply_response_auto_fix(text, evaluate_response(text))

    assert fixed == f"{REPEATED_SEGMENT}\nSonra soru çöz."


def test_normalized_equivalent_segments_collapse_without_rewriting_first() -> None:
    text = (
        "MATEMATİK yanlışlarını dikkatle analiz et.\n"
        "Matematik yanlışlarını dikkatle analiz et.\n"
        "matematik yanlışlarını dikkatle analiz et.\n"
        "Sonra soru çöz."
    )

    fixed = apply_response_auto_fix(text, evaluate_response(text))

    assert fixed == (
        "MATEMATİK yanlışlarını dikkatle analiz et.\nSonra soru çöz."
    )


def test_two_identical_segments_are_not_changed_by_runtime() -> None:
    text = repeated_text(2)
    orchestrator, _, provider, learner = make_runtime([text])

    result = orchestrator.respond(learner.learner_id, "Merhaba")

    assert result.text == text
    assert len(provider.requests) == 1


def test_non_consecutive_equal_segments_are_not_changed() -> None:
    text = (
        f"{REPEATED_SEGMENT}\nFizik konularını dikkatle tekrar et.\n"
        f"{REPEATED_SEGMENT}\n{REPEATED_SEGMENT}"
    )

    assert evaluate_response(text).action is ResponseValidationAction.PASS


def test_short_intervening_segment_breaks_repetition_run() -> None:
    text = (
        f"{REPEATED_SEGMENT}\nTamam.\n"
        f"{REPEATED_SEGMENT}\n{REPEATED_SEGMENT}"
    )
    orchestrator, _, provider, learner = make_runtime([text])

    assert repetition_duplicate_segment_indexes(text) == frozenset()
    assert evaluate_response(text).action is ResponseValidationAction.PASS

    result = orchestrator.respond(learner.learner_id, "Merhaba")

    assert result.text == text
    assert len(provider.requests) == 1


def test_unrelated_text_and_order_are_preserved() -> None:
    text = (
        "Önce kısa bir hazırlık yap.\n"
        + repeated_text(4, suffix="Ardından deneme çöz.\nSon olarak dinlen.")
    )

    fixed = apply_response_auto_fix(text, evaluate_response(text))

    assert fixed == (
        "Önce kısa bir hazırlık yap.\n"
        f"{REPEATED_SEGMENT}\n"
        "Ardından deneme çöz.\nSon olarak dinlen."
    )


def test_fix_removes_duplicates_without_changing_numeric_content() -> None:
    segment = "Matematik için tam 60 dakika tekrar yap."
    text = "\n".join([segment, segment, segment, "Sonra dinlen."])

    fixed = apply_response_auto_fix(text, evaluate_response(text))

    assert fixed == f"{segment}\nSonra dinlen."
    assert fixed.count("60") == 1


def test_wrong_report_action_is_rejected() -> None:
    with pytest.raises(ValueError, match="must be auto_fix"):
        apply_response_auto_fix("text", report(ResponseValidationAction.PASS))


def test_unsupported_auto_fix_violation_fails_closed() -> None:
    unsupported = report(ResponseValidationAction.AUTO_FIX, "UNKNOWN_AUTO_FIX")

    with pytest.raises(ResponseAutoFixRequired) as captured:
        apply_response_auto_fix(repeated_text(), unsupported)

    assert captured.value.report is unsupported


def test_validate_response_remains_a_non_fixing_compatibility_facade() -> None:
    with pytest.raises(ResponseValidationError) as captured:
        validate_response(repeated_text())

    assert captured.value.report.action is ResponseValidationAction.AUTO_FIX
    assert captured.value.violations == ["OUTPUT_REPETITION_LOOP"]


def test_runtime_auto_fix_revalidates_and_returns_fixed_text(monkeypatch) -> None:
    original_evaluator = coach_module.evaluate_response
    evaluator = Mock(side_effect=original_evaluator)
    monkeypatch.setattr(coach_module, "evaluate_response", evaluator)
    orchestrator, _, provider, learner = make_runtime([repeated_text()])

    result = orchestrator.respond(learner.learner_id, "Merhaba")

    assert result.text == f"{REPEATED_SEGMENT}\nSonra soru çöz."
    assert result.model == "model-1"
    assert len(provider.requests) == 1
    assert evaluator.call_count == 2


def test_structured_response_text_is_fixed_without_changing_proposal(
    monkeypatch,
) -> None:
    orchestrator, memory, provider, learner = make_runtime(
        [structured_response(repeated_text())]
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

    proposal = materialized[0]
    assert result.text == f"{REPEATED_SEGMENT}\nSonra soru çöz."
    assert result.study_plan_proposal is proposal
    assert result.study_plan_proposal.plan.plan_id == proposal.plan.plan_id
    assert result.study_plan_proposal.tasks[0].task_id == proposal.tasks[0].task_id
    assert result.study_plan_proposal.tasks[0].planned_minutes == 60
    assert result.study_plan_proposal.tasks[0].description == "Matematik çalış"
    assert len(provider.requests) == 1
    memory.save_study_plan.assert_not_called()


def test_regeneration_response_can_auto_fix_then_pass() -> None:
    orchestrator, _, provider, learner = make_runtime(
        ["Sen 10. sınıftasın.", repeated_text()]
    )

    result = orchestrator.respond(
        learner.learner_id,
        "Sınıfımı değerlendir",
    )

    assert result.text == f"{REPEATED_SEGMENT}\nSonra soru çöz."
    assert result.model == "model-2"
    assert len(provider.requests) == 2


def test_auto_fix_is_attempted_only_once_when_revalidation_is_auto_fix(
    monkeypatch,
) -> None:
    auto_report = report(
        ResponseValidationAction.AUTO_FIX,
        "OUTPUT_REPETITION_LOOP",
    )
    evaluator = Mock(side_effect=[auto_report, auto_report])
    fixer = Mock(wraps=apply_response_auto_fix)
    monkeypatch.setattr(coach_module, "evaluate_response", evaluator)
    monkeypatch.setattr(coach_module, "apply_response_auto_fix", fixer)
    orchestrator, _, provider, learner = make_runtime([repeated_text()])

    with pytest.raises(ResponseAutoFixRequired) as captured:
        orchestrator.respond(learner.learner_id, "Merhaba")

    assert captured.value.report is auto_report
    assert fixer.call_count == 1
    assert len(provider.requests) == 1


def test_auto_fix_revalidation_block_fails_closed(monkeypatch) -> None:
    auto_report = report(
        ResponseValidationAction.AUTO_FIX,
        "OUTPUT_REPETITION_LOOP",
    )
    block_report = report(
        ResponseValidationAction.BLOCK,
        "external_link_not_verified",
    )
    monkeypatch.setattr(
        coach_module,
        "evaluate_response",
        Mock(side_effect=[auto_report, block_report]),
    )
    orchestrator, _, provider, learner = make_runtime([repeated_text()])

    with pytest.raises(ResponseValidationError) as captured:
        orchestrator.respond(learner.learner_id, "Merhaba")

    assert type(captured.value) is ResponseValidationError
    assert captured.value.report is block_report
    assert len(provider.requests) == 1


def test_auto_fix_revalidation_can_trigger_one_regeneration(monkeypatch) -> None:
    auto_report = report(
        ResponseValidationAction.AUTO_FIX,
        "OUTPUT_REPETITION_LOOP",
    )
    regenerate_report = report(
        ResponseValidationAction.REGENERATE,
        "OUTPUT_UNSUPPORTED_GUARANTEE",
    )
    pass_report = report(ResponseValidationAction.PASS)
    monkeypatch.setattr(
        coach_module,
        "evaluate_response",
        Mock(side_effect=[auto_report, regenerate_report, pass_report]),
    )
    orchestrator, _, provider, learner = make_runtime(
        [repeated_text(), "Düzeltilmiş ikinci cevap."]
    )

    result = orchestrator.respond(learner.learner_id, "Merhaba")

    assert result.text == "Düzeltilmiş ikinci cevap."
    assert len(provider.requests) == 2


def test_auto_fix_after_final_regeneration_cannot_reset_budget(monkeypatch) -> None:
    regenerate_report = report(
        ResponseValidationAction.REGENERATE,
        "CORE_MEMORY_CONTRADICTION",
    )
    auto_report = report(
        ResponseValidationAction.AUTO_FIX,
        "OUTPUT_REPETITION_LOOP",
    )
    final_regenerate_report = report(
        ResponseValidationAction.REGENERATE,
        "OUTPUT_UNSUPPORTED_GUARANTEE",
    )
    monkeypatch.setattr(
        coach_module,
        "evaluate_response",
        Mock(
            side_effect=[
                regenerate_report,
                auto_report,
                final_regenerate_report,
            ]
        ),
    )
    orchestrator, _, provider, learner = make_runtime(
        ["first response", repeated_text()]
    )

    with pytest.raises(ResponseRegenerationExhausted) as captured:
        orchestrator.respond(learner.learner_id, "Merhaba")

    assert captured.value.report is final_regenerate_report
    assert len(provider.requests) == 2


def test_auto_fix_does_not_repeat_snapshot_context_intent_or_rag(monkeypatch) -> None:
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
        [repeated_text()],
        retriever=retriever,
    )
    message = "Aralıklı tekrar nasıl yapılır?"

    orchestrator.respond(learner.learner_id, message)

    assert len(provider.requests) == 1
    assert memory.get_learner_memory_snapshot.call_count == 1
    assert context_router.call_count == 1
    assert intent_detector.call_count == 1
    assert rag_gate.call_count == 1
    assert retriever.calls == [
        (message, {"program": {"global", "school_11"}})
    ]
