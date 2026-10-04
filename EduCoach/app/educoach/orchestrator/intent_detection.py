"""Conservative, deterministic intent detection for explicit message patterns."""

import re
import unicodedata

from .intent import IntentResolution, IntentType, resolve_intents


_GENERAL_CONVERSATION_MESSAGES = frozenset(
    {
        "günaydın",
        "merhaba",
        "selam",
        "teşekkür ederim",
        "teşekkürler",
    }
)


def detect_intents(message: str) -> IntentResolution:
    """Detect only intents supported by high-precision v0.1 rules."""

    normalized = _normalize(message)
    intents: list[IntentType] = []

    if _matches_planning(normalized):
        intents.append(IntentType.PLANNING)
    if _matches_assessment_analysis(normalized):
        intents.append(IntentType.ASSESSMENT_ANALYSIS)
    if _matches_goal_setting(normalized):
        intents.append(IntentType.GOAL_SETTING)
    if _matches_study_advice(normalized):
        intents.append(IntentType.STUDY_ADVICE)
    if _matches_knowledge_question(normalized):
        intents.append(IntentType.KNOWLEDGE_QUESTION)
    if _matches_motivation_support(normalized):
        intents.append(IntentType.MOTIVATION_SUPPORT)

    if not intents and normalized in _GENERAL_CONVERSATION_MESSAGES:
        intents.append(IntentType.GENERAL_CONVERSATION)

    return resolve_intents(intents)


def _normalize(message: str) -> str:
    normalized = unicodedata.normalize("NFKC", message)
    normalized = normalized.translate(str.maketrans({"I": "ı", "İ": "i"}))
    normalized = normalized.casefold()
    return " ".join(re.findall(r"\w+", normalized))


def _matches_planning(message: str) -> bool:
    plan_noun = r"\b(?:plan|program)\w*\b"
    plan_request = (
        r"\b(?:hazırla|oluştur|düzenle|yap)\b"
        r"|\b(?:hazırlar|oluşturur|düzenler|yapar)\s+mısın\b"
    )
    explicit_plan = (
        re.search(plan_noun, message) is not None
        and re.search(plan_request, message) is not None
    )
    what_to_study = re.search(
        r"\b(?:bugün|yarın|bu hafta)\b(?:\s+\w+){0,4}\s+ne\s+çalışayım\b",
        message,
    ) is not None
    return explicit_plan or what_to_study


def _matches_assessment_analysis(message: str) -> bool:
    numeric_performance = re.search(
        r"\b\d+(?:\s+\d+)?\s+(?:net|doğru|yanlış|boş)\b",
        message,
    ) is not None
    explicit_analysis = (
        re.search(r"\b(?:deneme|sınav)\w*\b", message) is not None
        and re.search(
            r"\banaliz\s+(?:et|eder\s+misin)\b",
            message,
        ) is not None
    )
    performance_change = re.search(
        r"\b(?:net|puan)\w*\b(?:\s+\w+){0,3}\s+"
        r"(?:düşt|azald|artt|yükseld)\w*\b",
        message,
    ) is not None
    return numeric_performance or explicit_analysis or performance_change


def _matches_study_advice(message: str) -> bool:
    how_to_study = re.search(
        r"\bnasıl\s+çalış(?:malıyım|ayım)\b",
        message,
    ) is not None
    advice_request = re.search(
        r"\bçalışma\s+öneri\w*\b(?:\s+\w+){0,3}\s+"
        r"(?:ver|söyle|verir\s+misin|söyler\s+misin)\b",
        message,
    ) is not None
    return how_to_study or advice_request


def _matches_goal_setting(message: str) -> bool:
    explicit_request = re.search(
        r"\bhedef\w*\b(?:\s+\w+){0,5}\s+"
        r"(?:belirle|koyalım|oluştur|belirlemek\s+istiyorum|"
        r"belirlememde\s+yardım\s+et)\b",
        message,
    )
    return explicit_request is not None


def _matches_motivation_support(message: str) -> bool:
    motivate_request = re.search(
        r"\bmotive\s+(?:et|eder\s+misin)\b",
        message,
    ) is not None
    motivation_need = re.search(
        r"\bmotivasyon\w*\b(?:\s+\w+){0,3}\s+ihtiyac\w*\s+var\b",
        message,
    ) is not None
    return motivate_request or motivation_need


def _matches_knowledge_question(message: str) -> bool:
    return re.search(r"\b(?:nedir|ne\s+demek)\b", message) is not None
