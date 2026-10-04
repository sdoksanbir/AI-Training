"""Typed contracts for deterministic multi-intent representation."""

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum


class IntentType(StrEnum):
    PLANNING = "planning"
    PROGRESS_REVIEW = "progress_review"
    ASSESSMENT_ANALYSIS = "assessment_analysis"
    GOAL_SETTING = "goal_setting"
    STUDY_ADVICE = "study_advice"
    KNOWLEDGE_QUESTION = "knowledge_question"
    MEMORY_UPDATE = "memory_update"
    TASK_UPDATE = "task_update"
    MOTIVATION_SUPPORT = "motivation_support"
    CLARIFICATION = "clarification"
    GENERAL_CONVERSATION = "general_conversation"


class IntentResolutionStatus(StrEnum):
    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"


_INTENT_ORDER = {intent: index for index, intent in enumerate(IntentType)}


@dataclass(frozen=True)
class IntentResolution:
    status: IntentResolutionStatus
    intents: tuple[IntentType, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.status, IntentResolutionStatus):
            raise ValueError("status must be an IntentResolutionStatus")
        if not isinstance(self.intents, tuple):
            raise ValueError("intents must be a tuple")
        if any(not isinstance(intent, IntentType) for intent in self.intents):
            raise ValueError("intents must contain only IntentType values")

        canonical = tuple(
            sorted(set(self.intents), key=_INTENT_ORDER.__getitem__)
        )
        object.__setattr__(self, "intents", canonical)

        if self.status == IntentResolutionStatus.RESOLVED and not canonical:
            raise ValueError("resolved intent resolution requires at least one intent")
        if self.status == IntentResolutionStatus.UNRESOLVED and canonical:
            raise ValueError("unresolved intent resolution cannot contain intents")


def resolve_intents(intents: Iterable[IntentType]) -> IntentResolution:
    """Normalize supplied intent identities without detecting or classifying."""

    intent_items = tuple(intents)
    status = (
        IntentResolutionStatus.RESOLVED
        if intent_items
        else IntentResolutionStatus.UNRESOLVED
    )
    return IntentResolution(status=status, intents=intent_items)
