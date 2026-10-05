"""Pure, deterministic RAG need gating for orchestrator requests."""

from dataclasses import dataclass
from enum import StrEnum
import re
import unicodedata

from .intent import IntentResolution, IntentResolutionStatus, IntentType


class RAGNeedStatus(StrEnum):
    REQUIRED = "required"
    NOT_REQUIRED = "not_required"
    UNRESOLVED = "unresolved"


class RAGNeedSource(StrEnum):
    EXTERNAL_KNOWLEDGE_SIGNAL = "external_knowledge_signal"
    REQUIRED_INTENT = "required_intent"
    LOCAL_INTENT = "local_intent"
    PLAN_ADJUSTMENT_SIGNAL = "plan_adjustment_signal"
    UNRESOLVED = "unresolved"


_REQUIRED_INTENTS = frozenset(
    {
        IntentType.KNOWLEDGE_QUESTION,
        IntentType.STUDY_ADVICE,
    }
)
_LOCAL_INTENTS = frozenset(
    {
        IntentType.GENERAL_CONVERSATION,
        IntentType.MOTIVATION_SUPPORT,
        IntentType.GOAL_SETTING,
        IntentType.ASSESSMENT_ANALYSIS,
        IntentType.PROGRESS_REVIEW,
        IntentType.MEMORY_UPDATE,
        IntentType.TASK_UPDATE,
        IntentType.CLARIFICATION,
        IntentType.PLANNING,
    }
)


@dataclass(frozen=True)
class RAGNeedDecision:
    status: RAGNeedStatus
    intents: tuple[IntentType, ...]
    source: RAGNeedSource

    def __post_init__(self) -> None:
        if not isinstance(self.status, RAGNeedStatus):
            raise ValueError("status must be a RAGNeedStatus")
        if not isinstance(self.source, RAGNeedSource):
            raise ValueError("source must be a RAGNeedSource")
        if not isinstance(self.intents, tuple):
            raise ValueError("intents must be a tuple")
        if any(not isinstance(intent, IntentType) for intent in self.intents):
            raise ValueError("intents must contain only IntentType values")
        if len(set(self.intents)) != len(self.intents):
            raise ValueError("intents cannot contain duplicates")
        if self.intents != _canonical_intents(self.intents):
            raise ValueError("intents must use canonical order")

        required_intents = set(self.intents) & _REQUIRED_INTENTS
        if self.source == RAGNeedSource.EXTERNAL_KNOWLEDGE_SIGNAL:
            if self.status != RAGNeedStatus.REQUIRED:
                raise ValueError("external knowledge signal requires RAG")
            return
        if self.source == RAGNeedSource.REQUIRED_INTENT:
            if self.status != RAGNeedStatus.REQUIRED or not required_intents:
                raise ValueError("required intent source requires a required intent")
            return
        if self.source == RAGNeedSource.LOCAL_INTENT:
            if (
                self.status != RAGNeedStatus.NOT_REQUIRED
                or not self.intents
                or required_intents
                or not set(self.intents).issubset(_LOCAL_INTENTS)
            ):
                raise ValueError("local intent source requires only local intents")
            return
        if self.source == RAGNeedSource.PLAN_ADJUSTMENT_SIGNAL:
            if self.status != RAGNeedStatus.NOT_REQUIRED or self.intents:
                raise ValueError(
                    "plan adjustment signal requires no resolved intents"
                )
            return
        if self.source == RAGNeedSource.UNRESOLVED:
            if self.status != RAGNeedStatus.UNRESOLVED or self.intents:
                raise ValueError("unresolved source requires no intents")
            return
        raise ValueError("unsupported RAG need source")


def decide_rag_need(
    message: str,
    intent_resolution: IntentResolution,
) -> RAGNeedDecision:
    """Decide whether curated knowledge retrieval is needed for a request."""

    if not isinstance(message, str):
        raise ValueError("message must be a string")
    if not isinstance(intent_resolution, IntentResolution):
        raise ValueError("intent_resolution must be an IntentResolution")

    normalized_message = _normalize(message)
    intents = intent_resolution.intents

    if _has_external_knowledge_signal(normalized_message):
        return RAGNeedDecision(
            RAGNeedStatus.REQUIRED,
            intents,
            RAGNeedSource.EXTERNAL_KNOWLEDGE_SIGNAL,
        )

    if set(intents) & _REQUIRED_INTENTS:
        return RAGNeedDecision(
            RAGNeedStatus.REQUIRED,
            intents,
            RAGNeedSource.REQUIRED_INTENT,
        )

    if (
        intent_resolution.status == IntentResolutionStatus.RESOLVED
        and set(intents).issubset(_LOCAL_INTENTS)
    ):
        return RAGNeedDecision(
            RAGNeedStatus.NOT_REQUIRED,
            intents,
            RAGNeedSource.LOCAL_INTENT,
        )

    if _has_plan_adjustment_signal(normalized_message):
        return RAGNeedDecision(
            RAGNeedStatus.NOT_REQUIRED,
            intents,
            RAGNeedSource.PLAN_ADJUSTMENT_SIGNAL,
        )

    return RAGNeedDecision(
        RAGNeedStatus.UNRESOLVED,
        intents,
        RAGNeedSource.UNRESOLVED,
    )


def _canonical_intents(intents: tuple[IntentType, ...]) -> tuple[IntentType, ...]:
    selected = set(intents)
    return tuple(intent for intent in IntentType if intent in selected)


def _normalize(message: str) -> str:
    normalized = unicodedata.normalize("NFKC", message).translate(
        str.maketrans({"I": "ı", "İ": "i"})
    )
    return " ".join(re.findall(r"[^\W_]+", normalized.casefold(), re.UNICODE))


def _has_external_knowledge_signal(message: str) -> bool:
    prerequisite_question = re.search(
        r"\b(?:bu\s+)?konu\w*\s+başlamadan\s+önce\s+"
        r"hangi\s+konu\w*\s+bilmeliyim\b",
        message,
    )
    current_exam_structure = re.search(
        r"\b(?:bu\s+)?sınav\w*\s+güncel\s+yapı\w*\s+"
        r"(?:nedir|nasıldır|nasıl)\b",
        message,
    )
    spaced_repetition_procedure = re.search(
        r"\baralıklı\s+tekrar\s+nasıl\s+yapılır\b",
        message,
    )
    return any(
        signal is not None
        for signal in (
            prerequisite_question,
            current_exam_structure,
            spaced_repetition_procedure,
        )
    )


def _has_plan_adjustment_signal(message: str) -> bool:
    return re.search(
        r"\b(?:plan|program)\w*\b(?:\s+[^\W_]+){0,6}\s+"
        r"(?:indir|azalt|kısalt|güncelle|değiştir)\w*\b",
        message,
        re.UNICODE,
    ) is not None
