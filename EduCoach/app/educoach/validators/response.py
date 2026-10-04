from decimal import Decimal
import re
from typing import TYPE_CHECKING
import unicodedata

from educoach.models import ContextStatus, ContextType, EvidenceState
from educoach.rules.assessment_facts import project_assessment_facts
from educoach.rules.coach_rules import validate_coach_response
from educoach.rules.contracts import RuleSeverity, RuleViolation

from .contracts import ResponseValidationAction, ResponseValidationReport

if TYPE_CHECKING:
    from educoach.services.snapshot import LearnerMemorySnapshot


_NUMBER = r"-?\d+(?:[.,]\d+)?"
_GRADE_CLAIM = re.compile(
    r"\b(?P<grade>(?:[5-9]|1[0-2]))\s*\.?\s*sinif"
    r"(?:tasin| ogrencisisin|ta okuyorsun)\b"
)
_PROGRAM_CLAIM = re.compile(
    r"\b(?P<program>yks|lgs|ales|kpss|yds|yokdil|toefl|ielts)"
    r"(?:['’]?(?:ye|ya|e|a))?\s+"
    r"(?:hazirlaniyorsun|ogrencisisin)\b"
)
_PROGRAM_CONTEXT_TYPES = {
    "yks": ContextType.ENTRANCE_EXAM,
    "lgs": ContextType.ENTRANCE_EXAM,
    "kpss": ContextType.PUBLIC_EXAM,
    "ales": ContextType.ACADEMIC_EXAM,
    "yds": ContextType.LANGUAGE_EXAM,
    "yokdil": ContextType.LANGUAGE_EXAM,
    "toefl": ContextType.LANGUAGE_EXAM,
    "ielts": ContextType.LANGUAGE_EXAM,
}
_WEAKNESS_CLAIMS = (
    re.compile(
        r"(?:^|[.!?]\s*)(?:kayitlara gore\s+)?(?:sen\s+)?"
        r"(?P<area>[a-z0-9_]+?)(?:larda|lerde|da|de|ta|te)\s+"
        r"(?:zayifsin|zorlaniyorsun|eksigin var)\b"
    ),
    re.compile(
        r"(?:^|[.!?]\s*)(?:kayitlara gore\s+)?(?:sen\s+)?"
        r"(?P<area>[a-z0-9_]+)\s+konusunda\s+"
        r"(?:zayifsin|zorlaniyorsun|eksigin var)\b"
    ),
)
_AREA_ALIASES = {
    "function": "fonksiyon",
    "functions": "fonksiyon",
    "math": "matematik",
    "mathematics": "matematik",
}
_ASSESSMENT_CLAIM_PATTERNS = (
    (
        "net",
        re.compile(
            rf"\bnetin\s+(?P<value>{_NUMBER})"
            r"(?=\s*(?:oldugu|olarak|dir\b|ydi\b|[.!?,]|$))"
        ),
    ),
    (
        "net",
        re.compile(
            rf"\b(?P<value>{_NUMBER})\s+net\s+"
            r"(?:yaptin|yapmissin|aldin|sonucun var)\b"
        ),
    ),
    (
        "score",
        re.compile(
            rf"\b(?:puanin|skorun)\s+(?P<value>{_NUMBER})"
            r"(?=\s*(?:oldugu|olarak|dir\b|ydi\b|[.!?,]|$))"
        ),
    ),
    (
        "score",
        re.compile(
            rf"\b(?P<value>{_NUMBER})\s+puan\s+"
            r"(?:aldin|almissin|sonucun var)\b"
        ),
    ),
    (
        "correct",
        re.compile(
            rf"\bdogru sayin\s+(?P<value>{_NUMBER})"
            r"(?=\s*(?:oldugu|[.!?,]|$))"
        ),
    ),
    (
        "correct",
        re.compile(rf"\b(?P<value>{_NUMBER})\s+dogrun\s+var\b"),
    ),
    (
        "incorrect",
        re.compile(
            rf"\byanlis sayin\s+(?P<value>{_NUMBER})"
            r"(?=\s*(?:oldugu|[.!?,]|$))"
        ),
    ),
    (
        "incorrect",
        re.compile(rf"\b(?P<value>{_NUMBER})\s+yanlisin\s+var\b"),
    ),
    (
        "blank",
        re.compile(
            rf"\bbos sayin\s+(?P<value>{_NUMBER})"
            r"(?=\s*(?:oldugu|[.!?,]|$))"
        ),
    ),
    (
        "blank",
        re.compile(rf"\b(?P<value>{_NUMBER})\s+bosun\s+var\b"),
    ),
    (
        "percentage",
        re.compile(
            rf"\bbasari oranin\s+yuzde\s+(?P<value>{_NUMBER})"
            r"(?=\s*(?:oldugu|[.!?,]|$))"
        ),
    ),
    (
        "percentage",
        re.compile(
            rf"\b(?:deneme|sinav|sonuc)[^.!?]{{0,40}}?%\s*"
            rf"(?P<value>{_NUMBER})"
        ),
    ),
    (
        "grade",
        re.compile(
            rf"\bnotun\s+(?P<value>{_NUMBER})"
            r"(?=\s*(?:oldugu|olarak|dir\b|ydi\b|[.!?,]|$))"
        ),
    ),
    (
        "duration_minutes",
        re.compile(
            rf"\b(?:deneme|sinav)(?:n|nin|in)?[^.!?]{{0,40}}?"
            rf"(?P<value>{_NUMBER})\s+dakika\s+surdu\b"
        ),
    ),
)


class ResponseValidationError(ValueError):
    def __init__(
        self,
        violations: list[str],
        report: ResponseValidationReport | None = None,
    ) -> None:
        self.violations = violations
        self.report = report
        super().__init__(f"Coach response rejected: {', '.join(violations)}")


def evaluate_response(
    text: str,
    *,
    snapshot: "LearnerMemorySnapshot | None" = None,
) -> ResponseValidationReport:
    legacy_violations = tuple(
        RuleViolation(
            rule_id=violation,
            severity=RuleSeverity.ERROR,
            message=violation,
        )
        for violation in validate_coach_response(text)
    )
    if legacy_violations:
        return ResponseValidationReport(
            action=ResponseValidationAction.BLOCK,
            violations=legacy_violations,
        )

    semantic_violations = (
        _evaluate_semantic_violations(text, snapshot)
        if snapshot is not None
        else ()
    )
    return ResponseValidationReport(
        action=(
            ResponseValidationAction.REGENERATE
            if semantic_violations
            else ResponseValidationAction.PASS
        ),
        violations=semantic_violations,
    )


def validate_response(
    text: str,
    *,
    snapshot: "LearnerMemorySnapshot | None" = None,
) -> str:
    report = evaluate_response(text, snapshot=snapshot)
    if report.action is not ResponseValidationAction.PASS:
        violations = [violation.rule_id for violation in report.violations]
        raise ResponseValidationError(violations, report=report)
    return text.strip()


def _evaluate_semantic_violations(
    text: str,
    snapshot: "LearnerMemorySnapshot",
) -> tuple[RuleViolation, ...]:
    normalized = _normalize_text(text)
    violations: list[RuleViolation] = []

    if _contradicts_grade_or_program(normalized, snapshot):
        _append_violation(
            violations,
            "CORE_MEMORY_CONTRADICTION",
            "Response contradicts recorded learner memory",
        )

    for claimed_area in _extract_weakness_claims(normalized):
        evidence_state = _recorded_area_state(claimed_area, snapshot)
        if evidence_state in (EvidenceState.STRONG, EvidenceState.ADEQUATE):
            _append_violation(
                violations,
                "CORE_MEMORY_CONTRADICTION",
                "Response contradicts recorded learner memory",
            )
        elif evidence_state not in (
            EvidenceState.WEAK,
            EvidenceState.DEVELOPING,
        ):
            _append_violation(
                violations,
                "CORE_UNKNOWN_FACT",
                "Response states an unsupported learner fact",
            )

    assessment_claims = _extract_assessment_claims(normalized)
    if assessment_claims:
        assessment_facts = project_assessment_facts(snapshot)
        for _, metric, value in assessment_claims:
            if _assessment_value_is_recorded(
                assessment_facts,
                metric,
                value,
            ):
                continue
            if (
                metric == "score"
                and _has_yks_context(snapshot)
                and _assessment_value_is_recorded(
                    assessment_facts,
                    "net",
                    value,
                )
            ):
                _append_violation(
                    violations,
                    "YKS_NET_SCORE_CONFUSION",
                    "Response presents a recorded YKS net as a score",
                )
            else:
                _append_violation(
                    violations,
                    "ASSESSMENT_UNKNOWN_RESULT",
                    "Response states an unrecorded assessment result",
                )

    return tuple(violations)


def _contradicts_grade_or_program(
    normalized: str,
    snapshot: "LearnerMemorySnapshot",
) -> bool:
    recorded_grades = _unique_values(
        context.grade_level
        for context in snapshot.contexts
        if context.status is ContextStatus.ACTIVE
        and context.grade_level is not None
    )
    if len(recorded_grades) == 1:
        for match in _GRADE_CLAIM.finditer(normalized):
            if int(match.group("grade")) != recorded_grades[0]:
                return True

    for match in _PROGRAM_CLAIM.finditer(normalized):
        claimed_program = match.group("program")
        context_type = _PROGRAM_CONTEXT_TYPES[claimed_program]
        comparable_contexts = [
            context
            for context in snapshot.contexts
            if context.status is ContextStatus.ACTIVE
            and context.context_type is context_type
        ]
        if comparable_contexts and all(
            _normalize_area(context.program_code) != claimed_program
            for context in comparable_contexts
        ):
            return True
    return False


def _extract_weakness_claims(normalized: str) -> list[str]:
    claims: list[tuple[int, str]] = []
    for pattern in _WEAKNESS_CLAIMS:
        for match in pattern.finditer(normalized):
            claim = (match.start(), _normalize_area(match.group("area")))
            if claim not in claims:
                claims.append(claim)
    claims.sort(key=lambda item: item[0])
    return [area for _, area in claims]


def _recorded_area_state(
    claimed_area: str,
    snapshot: "LearnerMemorySnapshot",
) -> EvidenceState | None:
    for evidence in snapshot.learning_evidence:
        if _normalize_area(evidence.area_code) == claimed_area:
            return evidence.state
    return None


def _extract_assessment_claims(
    normalized: str,
) -> list[tuple[int, str, Decimal]]:
    claims: list[tuple[int, str, Decimal]] = []
    seen: list[tuple[int, str, Decimal]] = []
    for metric, pattern in _ASSESSMENT_CLAIM_PATTERNS:
        for match in pattern.finditer(normalized):
            claim = (
                match.start(),
                metric,
                Decimal(match.group("value").replace(",", ".")),
            )
            if claim not in seen:
                seen.append(claim)
                claims.append(claim)
    claims.sort(key=lambda item: item[0])
    return claims


def _assessment_value_is_recorded(
    assessment_facts,
    metric: str,
    value: Decimal,
) -> bool:
    for assessment in assessment_facts.assessments:
        for result in assessment.results:
            recorded = getattr(result, metric)
            if recorded is not None and Decimal(str(recorded)) == value:
                return True
    return False


def _has_yks_context(snapshot: "LearnerMemorySnapshot") -> bool:
    return any(
        context.status is ContextStatus.ACTIVE
        and _normalize_area(context.program_code) == "yks"
        for context in snapshot.contexts
    )


def _append_violation(
    violations: list[RuleViolation],
    rule_id: str,
    message: str,
) -> None:
    if any(violation.rule_id == rule_id for violation in violations):
        return
    violations.append(
        RuleViolation(
            rule_id=rule_id,
            severity=RuleSeverity.ERROR,
            message=message,
        )
    )


def _unique_values(values) -> list:
    unique: list = []
    for value in values:
        if value not in unique:
            unique.append(value)
    return unique


def _normalize_text(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return "".join(
        character
        for character in decomposed
        if not unicodedata.combining(character)
    ).replace("ı", "i")


def _normalize_area(value: str) -> str:
    normalized = _normalize_text(value).strip().replace("_", " ")
    normalized = _AREA_ALIASES.get(normalized, normalized)
    if normalized.endswith(("lar", "ler")):
        normalized = normalized[:-3]
    return normalized


def validate_user_message(message: str) -> str:
    cleaned = message.strip()
    if not cleaned:
        raise ValueError("User message cannot be empty")
    if len(cleaned) > 12000:
        raise ValueError("User message is too long")
    return cleaned
