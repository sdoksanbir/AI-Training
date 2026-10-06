from datetime import date
from decimal import Decimal
import re
from typing import TYPE_CHECKING

from educoach.models import (
    ContextStatus,
    ContextType,
    EvidenceState,
    PlanType,
    StudyPlan,
    StudyTask,
    TaskType,
)
from educoach.rules.assessment_facts import project_assessment_facts
from educoach.rules.coach_rules import validate_coach_response
from educoach.rules.contracts import RuleSeverity, RuleViolation
from educoach.rules.context_specialty import project_context_specialty_facts
from educoach.rules.plan_budget import evaluate_plan_available_time_limit

from .contracts import ResponseValidationAction, ResponseValidationReport
from .repetition import normalize_response_text, repetition_duplicate_segment_indexes

if TYPE_CHECKING:
    from educoach.services.snapshot import LearnerMemorySnapshot
    from educoach.specialties import SpecialtyProfileRegistry


_NUMBER = r"-?\d+(?:[.,]\d+)?"
_HOUR_DURATION = rf"{_NUMBER}(?:\s*[-–—]\s*{_NUMBER})?\s+saat"
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
_COMPOUND_CONTEXT_CLAIM = re.compile(
    r"\b(?P<grade>(?:[5-9]|1[0-2]))\s*\.?\s*sinif\s+"
    r"(?P<program>yks|lgs|ales|kpss|yds|yokdil|toefl|ielts)\s+"
    r"ogrencisisin\b"
)
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
_PLAN_DATE_LINE = re.compile(
    r"(?m)^\s*(?:tarih\s*:\s*)?"
    r"(?P<date>\d{4}-\d{2}-\d{2})(?:\s+icin)?\s*:?\s*$"
)
_PLAN_BLOCK_LINE = re.compile(
    r"(?m)^\s*[-*]?\s*(?P<label>[a-z0-9_ ]{2,40}?)\s*:\s*"
    r"(?P<minutes>\d{1,3})\s+dakika\s*$"
)
_GUARANTEE_PATTERNS = (
    re.compile(
        r"\bkesin(?:likle)?\s+"
        r"(?:kazanirsin|basarirsin|hedefine ulasirsin)\b"
    ),
    re.compile(
        rf"\bmutlaka(?:\s+{_NUMBER}\s+net)?\s+"
        r"(?:artirirsin|kazanirsin|basarirsin)\b"
    ),
    re.compile(r"\b(?:kazanman|basarman)\s+garanti\b"),
    re.compile(
        r"\bbu\s+(?:plan|program)(?:la|le)\s+[^.!?\n]{0,80}?"
        r"(?:"
        r"(?:gereken|hedeflenen)\s+net(?:e|lere)\s+cikarsin|"
        r"hedef(?:e|ine)\s+ulasirsin|"
        r"net(?:ini|lerini)\s+artirirsin"
        r")\b"
    ),
)
_UNSAFE_HEALTH_INSTRUCTION_PATTERNS = (
    re.compile(
        rf"\b(?:(?:sinavdan\s+once\s+)?{_HOUR_DURATION}|"
        rf"sinavdan\s+{_HOUR_DURATION}\s+once)\s+"
        r"(?:su(?:yu)?(?:\s+icmeyi)?|sivi(?:yi)?(?:\s+alimini)?)\s+"
        r"(?:birak|kes|azalt)\b"
    ),
    re.compile(
        r"\b(?:su\s+icmeyi|sivi\s+alimini|yemeyi)\s+tamamen\s+"
        r"(?:birak|kes)\b"
    ),
    re.compile(
        r"\b(?:ilac\s+dozunu|ilacin\s+dozunu|dozunu)\s+"
        r"(?:[a-z0-9.,]+\s+){0,3}(?:artir|azalt|degistir)\b"
    ),
)
_PRESSURE_REINFORCEMENT_PATTERNS = (
    re.compile(r"\bkazanmak\s+zorundasin(?:iz)?\b"),
    re.compile(r"\bkazanma(?:n|niz)\s+sart\b"),
    re.compile(
        r"\b(?:tip\s+)?kazanmak\s+zorunlu\s+"
        r"oldugun(?:uz)?\s+icin\b"
    ),
    re.compile(r"\bkazanma(?:n|niz)\s+sart\s+oldugu\s+icin\b"),
)
_ACTION_PRECEDENCE = {
    ResponseValidationAction.PASS: 0,
    ResponseValidationAction.AUTO_FIX: 1,
    ResponseValidationAction.REGENERATE: 2,
    ResponseValidationAction.BLOCK: 3,
}


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
    specialty_registry: "SpecialtyProfileRegistry | None" = None,
) -> ResponseValidationReport:
    legacy_violations = tuple(
        RuleViolation(
            rule_id=violation,
            severity=RuleSeverity.ERROR,
            message=violation,
        )
        for violation in validate_coach_response(text)
    )
    semantic_violations = (
        _evaluate_semantic_violations(
            text,
            snapshot,
            specialty_registry=specialty_registry,
        )
        if snapshot is not None
        else _evaluate_output_violations(text)
    )
    return ResponseValidationReport(
        action=_highest_action(
            _legacy_validation_action(legacy_violations),
            _semantic_validation_action(semantic_violations),
        ),
        violations=legacy_violations + semantic_violations,
    )


def validate_response(
    text: str,
    *,
    snapshot: "LearnerMemorySnapshot | None" = None,
    specialty_registry: "SpecialtyProfileRegistry | None" = None,
) -> str:
    report = evaluate_response(
        text,
        snapshot=snapshot,
        specialty_registry=specialty_registry,
    )
    if report.action is not ResponseValidationAction.PASS:
        violations = [violation.rule_id for violation in report.violations]
        raise ResponseValidationError(violations, report=report)
    return text.strip()


def _evaluate_semantic_violations(
    text: str,
    snapshot: "LearnerMemorySnapshot",
    *,
    specialty_registry: "SpecialtyProfileRegistry | None",
) -> tuple[RuleViolation, ...]:
    normalized = _normalize_text(text)
    violations: list[RuleViolation] = []

    if _contradicts_grade_or_program(normalized, snapshot):
        _append_violation(
            violations,
            "CORE_MEMORY_CONTRADICTION",
            "Response contradicts recorded learner memory",
        )

    if (
        specialty_registry is not None
        and _contradicts_context_specialty(
            normalized,
            snapshot,
            specialty_registry,
        )
    ):
        _append_violation(
            violations,
            "CORE_CONTEXT_MISMATCH",
            "Response mixes or contradicts recorded context specialties",
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

    for violation in _evaluate_plan_violations(normalized, snapshot):
        _append_violation(
            violations,
            violation.rule_id,
            violation.message,
        )

    for violation in _evaluate_output_violations(text):
        _append_violation(
            violations,
            violation.rule_id,
            violation.message,
        )

    return tuple(violations)


def _evaluate_output_violations(text: str) -> tuple[RuleViolation, ...]:
    normalized = _normalize_text(text)
    violations: list[RuleViolation] = []
    if _has_repetition_loop(text):
        _append_violation(
            violations,
            "OUTPUT_REPETITION_LOOP",
            "Response contains a repeated output loop",
        )
    if _has_unsupported_guarantee(normalized):
        _append_violation(
            violations,
            "OUTPUT_UNSUPPORTED_GUARANTEE",
            "Response makes an unsupported outcome guarantee",
        )
    if _has_pressure_reinforcement(normalized):
        _append_violation(
            violations,
            "OUTPUT_PRESSURE_REINFORCEMENT",
            "Response reinforces absolute achievement pressure",
        )
    if _has_unsafe_health_instruction(normalized):
        _append_violation(
            violations,
            "OUTPUT_UNSAFE_HEALTH_INSTRUCTION",
            "Response gives a high-risk health instruction",
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


def _contradicts_context_specialty(
    normalized: str,
    snapshot: "LearnerMemorySnapshot",
    registry: "SpecialtyProfileRegistry",
) -> bool:
    facts = project_context_specialty_facts(snapshot, registry)
    active_context_ids = [
        context.context_id
        for context in snapshot.contexts
        if context.status is ContextStatus.ACTIVE
    ]
    active_facts = [
        fact for fact in facts if fact.context_id in active_context_ids
    ]

    for match in _PROGRAM_CLAIM.finditer(normalized):
        claimed_program = match.group("program")
        if active_facts and not any(
            _normalize_area(fact.profile_code) == claimed_program
            for fact in active_facts
        ):
            return True

    contexts_by_id = {
        context.context_id: context
        for context in snapshot.contexts
        if context.status is ContextStatus.ACTIVE
    }
    for match in _COMPOUND_CONTEXT_CLAIM.finditer(normalized):
        claimed_grade = int(match.group("grade"))
        claimed_program = match.group("program")
        if not any(
            contexts_by_id[fact.context_id].grade_level == claimed_grade
            and _normalize_area(fact.profile_code) == claimed_program
            for fact in active_facts
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


def _evaluate_plan_violations(
    normalized: str,
    snapshot: "LearnerMemorySnapshot",
) -> tuple[RuleViolation, ...]:
    plan_parts = _extract_explicit_daily_plan(normalized)
    if plan_parts is None:
        return ()
    target_date, blocks = plan_parts
    active_contexts = [
        context
        for context in snapshot.contexts
        if context.status is ContextStatus.ACTIVE
    ]
    if len(active_contexts) != 1:
        return ()

    context = active_contexts[0]
    candidate_plan = StudyPlan(
        learner_id=snapshot.learner.learner_id,
        context_id=context.context_id,
        title="Response daily plan",
        plan_type=PlanType.DAILY,
        start_date=target_date,
        end_date=target_date,
    )
    candidate_tasks = tuple(
        StudyTask(
            plan_id=candidate_plan.plan_id,
            context_id=context.context_id,
            task_date=target_date,
            task_type=TaskType.STUDY,
            description=label,
            planned_minutes=minutes,
        )
        for label, minutes in blocks
    )
    result = evaluate_plan_available_time_limit(
        snapshot,
        target_date,
        candidate_plan=candidate_plan,
        candidate_tasks=candidate_tasks,
    )
    return result.evaluation.violations


def _extract_explicit_daily_plan(
    normalized: str,
) -> tuple[date, tuple[tuple[str, int], ...]] | None:
    date_matches = list(_PLAN_DATE_LINE.finditer(normalized))
    if len(date_matches) != 1:
        return None
    try:
        target_date = date.fromisoformat(date_matches[0].group("date"))
    except ValueError:
        return None

    blocks = tuple(
        (match.group("label").strip(), int(match.group("minutes")))
        for match in _PLAN_BLOCK_LINE.finditer(normalized)
        if int(match.group("minutes")) > 0
    )
    if len(blocks) < 2:
        return None
    return target_date, blocks


def _has_repetition_loop(text: str) -> bool:
    return bool(repetition_duplicate_segment_indexes(text))


def _has_unsupported_guarantee(normalized: str) -> bool:
    for pattern in _GUARANTEE_PATTERNS:
        for match in pattern.finditer(normalized):
            tail = normalized[match.end(): match.end() + 24].lstrip()
            if tail.startswith(
                (
                    "diyemem",
                    "demiyorum",
                    "diye garanti yok",
                    "diye garanti edemem",
                )
            ):
                continue
            return True
    return False


def _has_unsafe_health_instruction(normalized: str) -> bool:
    return any(
        pattern.search(normalized)
        for pattern in _UNSAFE_HEALTH_INSTRUCTION_PATTERNS
    )


def _has_pressure_reinforcement(normalized: str) -> bool:
    for pattern in _PRESSURE_REINFORCEMENT_PATTERNS:
        for match in pattern.finditer(normalized):
            tail = normalized[match.end(): match.end() + 24].lstrip()
            if tail.startswith(("degil", "mi", "oldugunu dusun", "oldugunu hisset")):
                continue
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


def _highest_action(
    *actions: ResponseValidationAction,
) -> ResponseValidationAction:
    return max(actions, key=_ACTION_PRECEDENCE.__getitem__)


def _semantic_validation_action(
    violations: tuple[RuleViolation, ...],
) -> ResponseValidationAction:
    return _highest_action(
        *(
            ResponseValidationAction.AUTO_FIX
            if violation.rule_id == "OUTPUT_REPETITION_LOOP"
            else ResponseValidationAction.REGENERATE
            for violation in violations
        ),
        ResponseValidationAction.PASS,
    )


def _legacy_validation_action(
    violations: tuple[RuleViolation, ...],
) -> ResponseValidationAction:
    if not violations:
        return ResponseValidationAction.PASS
    if (
        len(violations) == 1
        and violations[0].rule_id == "external_link_not_verified"
    ):
        return ResponseValidationAction.REGENERATE
    return ResponseValidationAction.BLOCK


def _unique_values(values) -> list:
    unique: list = []
    for value in values:
        if value not in unique:
            unique.append(value)
    return unique


def _normalize_text(text: str) -> str:
    return normalize_response_text(text)


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
