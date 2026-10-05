from datetime import date
import json
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

import educoach.orchestrator.coach as coach_module
from educoach.llm import FakeLLMProvider, LLMRequest
from educoach.models import (
    Availability,
    AvailabilityType,
    ContextStatus,
    ContextType,
    DayOfWeek,
    Learner,
    LearningContext,
    PlanStatus,
    PlanType,
    TaskPriority,
    TaskStatus,
    TaskType,
)
from educoach.orchestrator import (
    CoachOrchestrator,
    StructuredLLMOutputError,
    StudyPlanProposal,
    materialize_study_plan_write_proposal,
    parse_structured_coach_output,
)
from educoach.services import LearnerMemoryService, LearnerMemorySnapshot
from educoach.validators import ResponseValidationAction, ResponseValidationReport
from educoach.writeback import WriteValidationStatus, validate_study_plan_write


MONDAY = date(2026, 10, 5)


def valid_payload() -> dict[str, object]:
    return {
        "response_text": "Planın hazır.",
        "proposal": {
            "title": "Haftalık çalışma planı",
            "plan_type": "weekly",
            "start_date": "2026-10-05",
            "end_date": "2026-10-05",
            "tasks": [
                {
                    "task_date": "2026-10-05",
                    "task_type": "study",
                    "description": "Matematik çalışma",
                    "planned_minutes": 60,
                    "priority": "high",
                    "area_type": "subject",
                    "area_code": "mathematics",
                }
            ],
        },
    }


def encoded(payload: dict[str, object]) -> str:
    return json.dumps(payload, ensure_ascii=False)


def test_valid_json_envelope_is_parsed() -> None:
    output = parse_structured_coach_output(encoded(valid_payload()))

    assert output.response_text == "Planın hazır."
    assert output.proposal is not None
    assert output.proposal.plan_type == PlanType.WEEKLY
    assert output.proposal.tasks[0].task_type == TaskType.STUDY
    assert output.proposal.tasks[0].priority == TaskPriority.HIGH


def test_null_proposal_is_valid() -> None:
    payload = {"response_text": "Daha fazla bilgi gerekli.", "proposal": None}

    output = parse_structured_coach_output(encoded(payload))

    assert output.proposal is None


@pytest.mark.parametrize(
    "raw_text",
    [
        "not json",
        "[1, 2]",
        'Önce açıklama. {"response_text":"x","proposal":null}',
        '{"response_text":"x","proposal":null} sonra açıklama',
        '```json\n{"response_text":"x","proposal":null}\n```',
    ],
)
def test_non_strict_json_output_is_rejected(raw_text: str) -> None:
    with pytest.raises(StructuredLLMOutputError):
        parse_structured_coach_output(raw_text)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda payload: payload.pop("response_text"),
        lambda payload: payload.__setitem__("response_text", "   "),
        lambda payload: payload.__setitem__("unknown", True),
        lambda payload: payload["proposal"].__setitem__("unknown", True),
    ],
)
def test_invalid_envelope_and_unknown_fields_are_rejected(mutate) -> None:
    payload = valid_payload()
    mutate(payload)

    with pytest.raises(StructuredLLMOutputError):
        parse_structured_coach_output(encoded(payload))


@pytest.mark.parametrize(
    ("location", "field"),
    [
        ("proposal", "learner_id"),
        ("proposal", "context_id"),
        ("proposal", "goal_id"),
        ("proposal", "plan_id"),
        ("proposal", "status"),
        ("proposal", "created_at"),
        ("proposal", "updated_at"),
        ("task", "task_id"),
        ("task", "plan_id"),
        ("task", "context_id"),
        ("task", "status"),
        ("task", "completed_at"),
    ],
)
def test_system_owned_field_injection_is_rejected(
    location: str,
    field: str,
) -> None:
    payload = valid_payload()
    target = (
        payload["proposal"]
        if location == "proposal"
        else payload["proposal"]["tasks"][0]
    )
    target[field] = str(uuid4()) if field.endswith("_id") else "active"

    with pytest.raises(StructuredLLMOutputError):
        parse_structured_coach_output(encoded(payload))


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("proposal", "plan_type"), "invalid"),
        (("task", "task_type"), "invalid"),
        (("task", "priority"), "invalid"),
        (("task", "planned_minutes"), 0),
        (("task", "planned_minutes"), -1),
        (("proposal", "title"), "  "),
        (("task", "description"), "  "),
    ],
)
def test_invalid_semantic_field_is_rejected(
    path: tuple[str, str],
    value: object,
) -> None:
    payload = valid_payload()
    scope, field = path
    target = (
        payload["proposal"]
        if scope == "proposal"
        else payload["proposal"]["tasks"][0]
    )
    target[field] = value

    with pytest.raises(StructuredLLMOutputError):
        parse_structured_coach_output(encoded(payload))


def test_end_before_start_is_rejected() -> None:
    payload = valid_payload()
    payload["proposal"]["end_date"] = "2026-10-04"

    with pytest.raises(StructuredLLMOutputError):
        parse_structured_coach_output(encoded(payload))


def test_empty_tasks_are_rejected() -> None:
    payload = valid_payload()
    payload["proposal"]["tasks"] = []

    with pytest.raises(StructuredLLMOutputError):
        parse_structured_coach_output(encoded(payload))


@pytest.mark.parametrize("missing_field", ["area_type", "area_code"])
def test_unpaired_area_field_is_rejected(missing_field: str) -> None:
    payload = valid_payload()
    payload["proposal"]["tasks"][0].pop(missing_field)

    with pytest.raises(StructuredLLMOutputError):
        parse_structured_coach_output(encoded(payload))


def test_omitted_priority_uses_authoritative_medium_default() -> None:
    payload = valid_payload()
    payload["proposal"]["tasks"][0].pop("priority")

    output = parse_structured_coach_output(encoded(payload))

    assert output.proposal is not None
    assert output.proposal.tasks[0].priority == TaskPriority.MEDIUM


def test_semantic_contract_is_deeply_immutable() -> None:
    output = parse_structured_coach_output(encoded(valid_payload()))
    assert output.proposal is not None

    with pytest.raises(ValidationError):
        output.response_text = "changed"
    with pytest.raises(ValidationError):
        output.proposal.title = "changed"
    with pytest.raises(ValidationError):
        output.proposal.tasks[0].description = "changed"


def make_context(
    learner: Learner,
    *,
    status: ContextStatus = ContextStatus.ACTIVE,
) -> LearningContext:
    return LearningContext(
        learner_id=learner.learner_id,
        context_type=ContextType.SCHOOL,
        program_code="school_program",
        status=status,
    )


def make_snapshot(
    learner: Learner,
    contexts: tuple[LearningContext, ...],
    *,
    availability: tuple[Availability, ...] = (),
) -> LearnerMemorySnapshot:
    return LearnerMemorySnapshot(
        learner=learner,
        contexts=contexts,
        goals=(),
        availability=availability,
        assessments=(),
        assessment_results=(),
        learning_evidence=(),
        study_plans=(),
        study_tasks=(),
        study_sessions=(),
        preferences=(),
        coaching_states=(),
    )


def semantic_proposal() -> StudyPlanProposal:
    output = parse_structured_coach_output(encoded(valid_payload()))
    assert output.proposal is not None
    return output.proposal


def test_materialization_binds_all_system_owned_fields_and_preserves_semantics() -> None:
    learner = Learner()
    context = make_context(learner)
    snapshot = make_snapshot(learner, (context,))
    semantic = semantic_proposal()

    write_proposal = materialize_study_plan_write_proposal(
        semantic, snapshot, context
    )
    plan = write_proposal.plan
    task = write_proposal.tasks[0]

    assert plan.learner_id == snapshot.learner.learner_id
    assert plan.context_id == context.context_id
    assert isinstance(plan.plan_id, UUID)
    assert task.context_id == context.context_id
    assert task.plan_id == plan.plan_id
    assert isinstance(task.task_id, UUID)
    assert plan.status == PlanStatus.DRAFT
    assert task.status == TaskStatus.PENDING
    assert plan.title == semantic.title
    assert plan.plan_type == semantic.plan_type
    assert plan.start_date == semantic.start_date
    assert plan.end_date == semantic.end_date
    assert task.description == semantic.tasks[0].description
    assert task.planned_minutes == semantic.tasks[0].planned_minutes
    assert task.area_type == semantic.tasks[0].area_type
    assert task.area_code == semantic.tasks[0].area_code
    assert task.priority == semantic.tasks[0].priority


def test_each_materialization_generates_fresh_system_ids() -> None:
    learner = Learner()
    context = make_context(learner)
    snapshot = make_snapshot(learner, (context,))
    semantic = semantic_proposal()

    first = materialize_study_plan_write_proposal(semantic, snapshot, context)
    second = materialize_study_plan_write_proposal(semantic, snapshot, context)

    assert first.plan.plan_id != second.plan.plan_id
    assert first.tasks[0].task_id != second.tasks[0].task_id


def test_materialization_binds_every_task_to_generated_plan_and_context() -> None:
    learner = Learner()
    context = make_context(learner)
    snapshot = make_snapshot(learner, (context,))
    payload = valid_payload()
    second_task = dict(payload["proposal"]["tasks"][0])
    second_task["description"] = "Fen çalışma"
    second_task["area_code"] = "science"
    payload["proposal"]["tasks"].append(second_task)
    output = parse_structured_coach_output(encoded(payload))
    assert output.proposal is not None

    materialized = materialize_study_plan_write_proposal(
        output.proposal, snapshot, context
    )

    assert len(materialized.tasks) == 2
    assert {task.plan_id for task in materialized.tasks} == {
        materialized.plan.plan_id
    }
    assert {task.context_id for task in materialized.tasks} == {
        context.context_id
    }
    assert len({task.task_id for task in materialized.tasks}) == 2


def test_materialization_rejects_non_authoritative_context() -> None:
    learner = Learner()
    context = make_context(learner)
    foreign = make_context(Learner())
    snapshot = make_snapshot(learner, (context,))

    with pytest.raises(ValueError, match="authoritative snapshot context"):
        materialize_study_plan_write_proposal(
            semantic_proposal(), snapshot, foreign
        )


def test_materialized_proposal_is_compatible_with_existing_write_validator() -> None:
    learner = Learner()
    context = make_context(learner)
    availability = Availability(
        learner_id=learner.learner_id,
        day_of_week=DayOfWeek.MONDAY,
        availability_type=AvailabilityType.AVAILABLE,
        available_minutes=120,
    )
    snapshot = make_snapshot(learner, (context,), availability=(availability,))
    proposal = materialize_study_plan_write_proposal(
        semantic_proposal(), snapshot, context
    )

    assert validate_study_plan_write(snapshot, proposal).status == (
        WriteValidationStatus.VALID
    )


class RecordingRetriever:
    def __init__(self) -> None:
        self.calls: list[dict[str, str | set[str]] | None] = []

    def search(
        self,
        query: str,
        limit: int = 3,
        filters: dict[str, str | set[str]] | None = None,
    ) -> list[object]:
        self.calls.append(filters)
        return []


def structured_text(*, response_text: str = "Planın hazır.", proposal=True) -> str:
    payload = valid_payload()
    payload["response_text"] = response_text
    if not proposal:
        payload["proposal"] = None
    return encoded(payload)


def make_runtime(
    snapshot: LearnerMemorySnapshot,
    response_text: str,
    *,
    retriever: RecordingRetriever | None = None,
) -> tuple[CoachOrchestrator, Mock, FakeLLMProvider]:
    memory = Mock(spec=LearnerMemoryService)
    memory.get_learner_memory_snapshot.return_value = snapshot
    provider = FakeLLMProvider(responder=lambda _: response_text)
    return CoachOrchestrator(memory, provider, retriever), memory, provider


def test_planning_resolved_uses_structured_prompt_and_single_provider_call() -> None:
    learner = Learner()
    context = make_context(learner)
    orchestrator, memory, provider = make_runtime(
        make_snapshot(learner, (context,)), structured_text()
    )

    result = orchestrator.respond(learner.learner_id, "Bana haftalık plan yap.")

    assert len(provider.requests) == 1
    request = provider.requests[0]
    assert isinstance(request, LLMRequest)
    assert "ONLY valid JSON object" in request.system_prompt
    assert "proposal null" in request.system_prompt
    assert all(item.value in request.system_prompt for item in PlanType)
    assert all(item.value in request.system_prompt for item in TaskType)
    assert all(item.value in request.system_prompt for item in TaskPriority)
    assert not hasattr(request, "response_format")
    assert result.text == "Planın hazır."
    assert result.study_plan_proposal is not None
    memory.save_study_plan.assert_not_called()


def test_structured_null_proposal_returns_text_without_candidate() -> None:
    learner = Learner()
    context = make_context(learner)
    orchestrator, memory, _ = make_runtime(
        make_snapshot(learner, (context,)),
        structured_text(response_text="Uygun süreni bilmeliyim.", proposal=False),
    )

    result = orchestrator.respond(learner.learner_id, "Bana günlük plan yap.")

    assert result.text == "Uygun süreni bilmeliyim."
    assert result.study_plan_proposal is None
    memory.save_study_plan.assert_not_called()


def test_malformed_structured_output_fails_closed_without_persistence() -> None:
    learner = Learner()
    context = make_context(learner)
    orchestrator, memory, provider = make_runtime(
        make_snapshot(learner, (context,)), "not json"
    )

    with pytest.raises(StructuredLLMOutputError):
        orchestrator.respond(learner.learner_id, "Bana haftalık plan yap.")

    assert len(provider.requests) == 1
    memory.save_study_plan.assert_not_called()


def test_response_validator_receives_response_text_not_raw_json(monkeypatch) -> None:
    learner = Learner()
    context = make_context(learner)
    raw = structured_text(response_text="Gösterilecek cevap.")
    orchestrator, _, _ = make_runtime(make_snapshot(learner, (context,)), raw)
    validator = Mock(
        return_value=ResponseValidationReport(ResponseValidationAction.PASS)
    )
    monkeypatch.setattr(coach_module, "evaluate_response", validator)

    result = orchestrator.respond(learner.learner_id, "Bana haftalık plan yap.")

    assert result.text == "Gösterilecek cevap."
    assert validator.call_args.args[0] == "Gösterilecek cevap."
    assert validator.call_args.args[0] != raw


def test_unsafe_structured_response_text_is_rejected_by_existing_validator() -> None:
    learner = Learner()
    context = make_context(learner)
    orchestrator, memory, _ = make_runtime(
        make_snapshot(learner, (context,)),
        structured_text(response_text="Kaynak: https://example.com"),
    )

    with pytest.raises(ValueError, match="external_link_not_verified"):
        orchestrator.respond(learner.learner_id, "Bana haftalık plan yap.")

    memory.save_study_plan.assert_not_called()


def test_non_planning_keeps_plain_text_path_and_no_proposal() -> None:
    learner = Learner()
    context = make_context(learner)
    orchestrator, _, provider = make_runtime(
        make_snapshot(learner, (context,)), "Düz metin cevap."
    )

    result = orchestrator.respond(learner.learner_id, "Merhaba")

    assert result.text == "Düz metin cevap."
    assert result.study_plan_proposal is None
    assert "ONLY valid JSON object" not in provider.requests[0].system_prompt


def test_planning_with_zero_active_context_keeps_plain_text_path() -> None:
    learner = Learner()
    orchestrator, _, provider = make_runtime(
        make_snapshot(learner, ()), "Bağlam olmadan düz cevap."
    )

    result = orchestrator.respond(learner.learner_id, "Bana haftalık plan yap.")

    assert result.text == "Bağlam olmadan düz cevap."
    assert result.study_plan_proposal is None
    assert "ONLY valid JSON object" not in provider.requests[0].system_prompt


def test_ambiguous_context_still_stops_before_provider() -> None:
    learner = Learner()
    first = make_context(learner)
    second = LearningContext(
        learner_id=learner.learner_id,
        context_type=ContextType.OTHER,
        program_code="other_program",
    )
    orchestrator, _, provider = make_runtime(
        make_snapshot(learner, (first, second)), structured_text()
    )

    result = orchestrator.respond(learner.learner_id, "Bana haftalık plan yap.")

    assert result.model == "deterministic"
    assert provider.requests == []


def test_invalid_explicit_context_still_stops_before_provider() -> None:
    learner = Learner()
    context = make_context(learner)
    orchestrator, _, provider = make_runtime(
        make_snapshot(learner, (context,)), structured_text()
    )

    with pytest.raises(ValueError, match="requested context"):
        orchestrator.respond(
            learner.learner_id,
            "Bana haftalık plan yap.",
            context_id=uuid4(),
        )

    assert provider.requests == []


def test_planning_and_study_advice_preserve_rag_scope() -> None:
    learner = Learner()
    context = make_context(learner)
    retriever = RecordingRetriever()
    orchestrator, _, _ = make_runtime(
        make_snapshot(learner, (context,)),
        structured_text(proposal=False),
        retriever=retriever,
    )
    message = "Bana haftalık plan yap ve nasıl çalışmalıyım?"

    orchestrator.respond(learner.learner_id, message)

    assert retriever.calls == [
        {"program": {"global", context.program_code}}
    ]


def test_structured_planning_works_without_retriever() -> None:
    learner = Learner()
    context = make_context(learner)
    orchestrator, _, provider = make_runtime(
        make_snapshot(learner, (context,)), structured_text(proposal=False)
    )

    result = orchestrator.respond(learner.learner_id, "Bana haftalık plan yap.")

    assert result.text == "Planın hazır."
    assert len(provider.requests) == 1
