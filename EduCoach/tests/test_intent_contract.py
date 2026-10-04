from dataclasses import FrozenInstanceError

import pytest

from educoach.orchestrator import (
    IntentResolution,
    IntentResolutionStatus,
    IntentType,
    resolve_intents,
)


EXPECTED_INTENTS = {
    "planning",
    "progress_review",
    "assessment_analysis",
    "goal_setting",
    "study_advice",
    "knowledge_question",
    "memory_update",
    "task_update",
    "motivation_support",
    "clarification",
    "general_conversation",
}


def test_intent_type_contains_exactly_the_documented_family() -> None:
    assert {intent.value for intent in IntentType} == EXPECTED_INTENTS
    assert len(IntentType) == 11


def test_single_intent_is_resolved() -> None:
    result = resolve_intents((IntentType.PLANNING,))

    assert result == IntentResolution(
        IntentResolutionStatus.RESOLVED,
        (IntentType.PLANNING,),
    )


def test_multiple_intents_are_supported() -> None:
    result = resolve_intents(
        (IntentType.ASSESSMENT_ANALYSIS, IntentType.PLANNING)
    )

    assert result.status == IntentResolutionStatus.RESOLVED
    assert result.intents == (
        IntentType.PLANNING,
        IntentType.ASSESSMENT_ANALYSIS,
    )


def test_empty_collection_is_unresolved_with_no_intents() -> None:
    result = resolve_intents(())

    assert result.status == IntentResolutionStatus.UNRESOLVED
    assert result.intents == ()


def test_general_conversation_is_a_real_resolved_intent() -> None:
    conversation = resolve_intents((IntentType.GENERAL_CONVERSATION,))
    unresolved = resolve_intents(())

    assert conversation.status == IntentResolutionStatus.RESOLVED
    assert conversation.intents == (IntentType.GENERAL_CONVERSATION,)
    assert conversation != unresolved


def test_input_order_produces_the_same_canonical_result() -> None:
    forward = resolve_intents(
        (IntentType.PLANNING, IntentType.ASSESSMENT_ANALYSIS)
    )
    reverse = resolve_intents(
        (IntentType.ASSESSMENT_ANALYSIS, IntentType.PLANNING)
    )

    assert forward == reverse


def test_duplicate_intents_are_canonically_deduplicated() -> None:
    result = resolve_intents(
        (
            IntentType.PLANNING,
            IntentType.ASSESSMENT_ANALYSIS,
            IntentType.PLANNING,
        )
    )

    assert result.intents == (
        IntentType.PLANNING,
        IntentType.ASSESSMENT_ANALYSIS,
    )


def test_direct_contract_construction_is_also_canonical() -> None:
    result = IntentResolution(
        IntentResolutionStatus.RESOLVED,
        (
            IntentType.TASK_UPDATE,
            IntentType.PLANNING,
            IntentType.TASK_UPDATE,
        ),
    )

    assert result.intents == (IntentType.PLANNING, IntentType.TASK_UPDATE)


def test_resolved_contract_requires_an_intent() -> None:
    with pytest.raises(ValueError, match="at least one intent"):
        IntentResolution(IntentResolutionStatus.RESOLVED, ())


def test_unresolved_contract_rejects_intents() -> None:
    with pytest.raises(ValueError, match="cannot contain intents"):
        IntentResolution(
            IntentResolutionStatus.UNRESOLVED,
            (IntentType.PLANNING,),
        )


def test_contract_requires_an_immutable_tuple() -> None:
    with pytest.raises(ValueError, match="tuple"):
        IntentResolution(
            IntentResolutionStatus.RESOLVED,
            [IntentType.PLANNING],
        )


def test_contract_rejects_untyped_intent_values() -> None:
    with pytest.raises(ValueError, match="IntentType"):
        IntentResolution(
            IntentResolutionStatus.RESOLVED,
            ("planning",),
        )


def test_result_and_intent_tuple_are_immutable() -> None:
    result = resolve_intents((IntentType.PLANNING,))

    with pytest.raises(FrozenInstanceError):
        result.status = IntentResolutionStatus.UNRESOLVED
    with pytest.raises(TypeError):
        result.intents[0] = IntentType.STUDY_ADVICE


def test_same_input_is_repeatable() -> None:
    intents = (IntentType.KNOWLEDGE_QUESTION, IntentType.STUDY_ADVICE)

    assert resolve_intents(intents) == resolve_intents(intents)
