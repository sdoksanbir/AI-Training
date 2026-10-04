from dataclasses import FrozenInstanceError
from datetime import date

import pytest

from educoach.models import (
    Assessment,
    AssessmentResult,
    ContextType,
    EvidenceSource,
    EvidenceState,
    Learner,
    LearningContext,
    LearningEvidence,
)
from educoach.rules.contracts import RuleSeverity, RuleViolation
from educoach.services.snapshot import LearnerMemorySnapshot
from educoach.validators import (
    ResponseValidationAction,
    ResponseValidationError,
    evaluate_response,
    validate_response,
)


def make_contextual_snapshot(
    *,
    grade_level: int = 11,
    program_code: str = "yks",
    evidence_code: str | None = None,
    evidence_state: EvidenceState = EvidenceState.WEAK,
    assessment_metrics: dict | None = None,
) -> LearnerMemorySnapshot:
    learner = Learner(display_name="Ali")
    context = LearningContext(
        learner_id=learner.learner_id,
        context_type=ContextType.ENTRANCE_EXAM,
        program_code=program_code,
        grade_level=grade_level,
    )
    evidence = (
        LearningEvidence(
            learner_id=learner.learner_id,
            context_id=context.context_id,
            area_type="subject",
            area_code=evidence_code,
            state=evidence_state,
            source_type=EvidenceSource.LEARNER_REPORTED,
        ),
    ) if evidence_code is not None else ()
    assessments: tuple[Assessment, ...] = ()
    results: tuple[AssessmentResult, ...] = ()
    if assessment_metrics is not None:
        assessment = Assessment(
            learner_id=learner.learner_id,
            context_id=context.context_id,
            assessment_type="mock_exam",
            assessment_name="TYT denemesi",
            assessment_date=date(2026, 10, 4),
        )
        assessments = (assessment,)
        results = (
            AssessmentResult(
                assessment_id=assessment.assessment_id,
                area_type="section",
                area_code="tyt",
                **assessment_metrics,
            ),
        )
    return LearnerMemorySnapshot(
        learner=learner,
        contexts=(context,),
        goals=(),
        availability=(),
        assessments=assessments,
        assessment_results=results,
        learning_evidence=evidence,
        study_plans=(),
        study_tasks=(),
        study_sessions=(),
        preferences=(),
        coaching_states=(),
    )


def test_normal_response_produces_pass_report() -> None:
    report = evaluate_response("Bugün matematik çalışabilirsin.")

    assert report.action is ResponseValidationAction.PASS
    assert report.violations == ()


def test_validate_response_strips_normal_response() -> None:
    assert validate_response("  Hazırım.  ") == "Hazırım."


@pytest.mark.parametrize(
    ("text", "expected_rule_id"),
    [
        ("   ", "empty_response"),
        ("x" * 12001, "response_too_long"),
        ("Kaynak: https://example.com", "external_link_not_verified"),
    ],
)
def test_legacy_violations_produce_block_report(
    text: str,
    expected_rule_id: str,
) -> None:
    report = evaluate_response(text)

    assert report.action is ResponseValidationAction.BLOCK
    assert [violation.rule_id for violation in report.violations] == [
        expected_rule_id
    ]


def test_block_report_uses_existing_rule_violation_contract() -> None:
    report = evaluate_response("Kaynak: www.example.com")

    violation = report.violations[0]
    assert isinstance(violation, RuleViolation)
    assert violation.rule_id == "external_link_not_verified"
    assert violation.severity is RuleSeverity.ERROR
    assert violation.message == "external_link_not_verified"


def test_response_validation_report_is_immutable() -> None:
    report = evaluate_response("Geçerli cevap")

    assert isinstance(report.violations, tuple)
    with pytest.raises(FrozenInstanceError):
        report.action = ResponseValidationAction.BLOCK


def test_response_validation_error_preserves_legacy_violations() -> None:
    with pytest.raises(ResponseValidationError) as captured:
        validate_response("   ")

    assert captured.value.violations == ["empty_response"]
    assert captured.value.report is not None
    assert captured.value.report.action is ResponseValidationAction.BLOCK


def test_response_validation_error_is_still_a_value_error() -> None:
    with pytest.raises(ValueError, match="external_link_not_verified"):
        validate_response("https://example.com")


def test_all_response_validation_actions_are_available() -> None:
    assert list(ResponseValidationAction) == [
        ResponseValidationAction.PASS,
        ResponseValidationAction.AUTO_FIX,
        ResponseValidationAction.REGENERATE,
        ResponseValidationAction.BLOCK,
    ]
    assert [action.value for action in ResponseValidationAction] == [
        "pass",
        "auto_fix",
        "regenerate",
        "block",
    ]


def test_legacy_violation_order_is_preserved() -> None:
    prefix = "https://example.com"
    report = evaluate_response(prefix + "x" * (12001 - len(prefix)))

    assert [violation.rule_id for violation in report.violations] == [
        "response_too_long",
        "external_link_not_verified",
    ]


def test_response_length_boundary_is_preserved() -> None:
    assert evaluate_response("x" * 12000).action is ResponseValidationAction.PASS

    report = evaluate_response("x" * 12001)
    assert report.action is ResponseValidationAction.BLOCK
    assert [violation.rule_id for violation in report.violations] == [
        "response_too_long"
    ]


def test_recorded_grade_and_program_claims_pass() -> None:
    report = evaluate_response(
        "Sen 11. sınıftasın ve YKS'ye hazırlanıyorsun.",
        snapshot=make_contextual_snapshot(),
    )

    assert report.action is ResponseValidationAction.PASS


def test_explicit_wrong_grade_regenerates() -> None:
    report = evaluate_response(
        "Sen 10. sınıftasın.",
        snapshot=make_contextual_snapshot(grade_level=11),
    )

    assert report.action is ResponseValidationAction.REGENERATE
    assert [violation.rule_id for violation in report.violations] == [
        "CORE_MEMORY_CONTRADICTION"
    ]


def test_explicit_conflicting_program_regenerates() -> None:
    report = evaluate_response(
        "LGS'ye hazırlanıyorsun.",
        snapshot=make_contextual_snapshot(program_code="yks"),
    )

    assert report.action is ResponseValidationAction.REGENERATE
    assert report.violations[0].rule_id == "CORE_MEMORY_CONTRADICTION"


def test_general_grade_language_does_not_create_false_positive() -> None:
    report = evaluate_response(
        "Sınıf düzeyine uygun sorularla ilerleyebilirsin.",
        snapshot=make_contextual_snapshot(),
    )

    assert report.action is ResponseValidationAction.PASS


def test_recorded_specific_weakness_claim_passes() -> None:
    report = evaluate_response(
        "Fonksiyonlarda zayıfsın.",
        snapshot=make_contextual_snapshot(evidence_code="functions"),
    )

    assert report.action is ResponseValidationAction.PASS


def test_unrecorded_specific_weakness_regenerates() -> None:
    report = evaluate_response(
        "Fonksiyonlarda zayıfsın.",
        snapshot=make_contextual_snapshot(evidence_code="mathematics"),
    )

    assert report.action is ResponseValidationAction.REGENERATE
    assert report.violations[0].rule_id == "CORE_UNKNOWN_FACT"


def test_weakness_claim_against_strong_evidence_is_contradiction() -> None:
    report = evaluate_response(
        "Matematikte zorlanıyorsun.",
        snapshot=make_contextual_snapshot(
            evidence_code="mathematics",
            evidence_state=EvidenceState.STRONG,
        ),
    )

    assert report.action is ResponseValidationAction.REGENERATE
    assert report.violations[0].rule_id == "CORE_MEMORY_CONTRADICTION"


def test_specific_topic_recommendation_is_not_a_learner_fact() -> None:
    report = evaluate_response(
        "Fonksiyonlara 30 dakika ayırmanı öneririm.",
        snapshot=make_contextual_snapshot(evidence_code="mathematics"),
    )

    assert report.action is ResponseValidationAction.PASS


def test_recorded_net_claim_passes() -> None:
    report = evaluate_response(
        "Son denemede 74 net yaptın.",
        snapshot=make_contextual_snapshot(assessment_metrics={"net": 74}),
    )

    assert report.action is ResponseValidationAction.PASS


def test_unrecorded_net_claim_regenerates() -> None:
    report = evaluate_response(
        "Son denemede 75 net yaptın.",
        snapshot=make_contextual_snapshot(assessment_metrics={"net": 74}),
    )

    assert report.action is ResponseValidationAction.REGENERATE
    assert report.violations[0].rule_id == "ASSESSMENT_UNKNOWN_RESULT"


def test_recorded_score_claim_passes() -> None:
    report = evaluate_response(
        "Son denemede 410 puan aldın.",
        snapshot=make_contextual_snapshot(assessment_metrics={"score": 410}),
    )

    assert report.action is ResponseValidationAction.PASS


def test_recorded_net_presented_as_score_regenerates() -> None:
    report = evaluate_response(
        "TYT puanın 74 olduğu için bu konuya odaklanmalısın.",
        snapshot=make_contextual_snapshot(assessment_metrics={"net": 74}),
    )

    assert report.action is ResponseValidationAction.REGENERATE
    assert report.violations[0].rule_id == "YKS_NET_SCORE_CONFUSION"


def test_unrecorded_result_metric_regenerates() -> None:
    report = evaluate_response(
        "Doğru sayın 30.",
        snapshot=make_contextual_snapshot(assessment_metrics={"net": 74}),
    )

    assert report.action is ResponseValidationAction.REGENERATE
    assert report.violations[0].rule_id == "ASSESSMENT_UNKNOWN_RESULT"


@pytest.mark.parametrize(
    ("metrics", "text"),
    [
        ({"correct": 30}, "Doğru sayın 30."),
        ({"incorrect": 6}, "Yanlış sayın 6."),
        ({"blank": 4}, "Boş sayın 4."),
        ({"percentage": 75}, "Başarı oranın yüzde 75."),
        ({"grade": 80}, "Notun 80."),
        ({"duration_minutes": 120}, "Denemen 120 dakika sürdü."),
    ],
)
def test_each_recorded_assessment_metric_remains_distinct(
    metrics: dict,
    text: str,
) -> None:
    report = evaluate_response(
        text,
        snapshot=make_contextual_snapshot(assessment_metrics=metrics),
    )

    assert report.action is ResponseValidationAction.PASS


def test_recommendation_numbers_are_not_assessment_claims() -> None:
    report = evaluate_response(
        "40 dakika çalış, 20 soru çöz ve 2 tekrar yap.",
        snapshot=make_contextual_snapshot(assessment_metrics={"net": 74}),
    )

    assert report.action is ResponseValidationAction.PASS


def test_multiple_semantic_violations_have_deterministic_order() -> None:
    report = evaluate_response(
        "Sen 10. sınıftasın. Fonksiyonlarda zayıfsın. Netin 80.",
        snapshot=make_contextual_snapshot(
            grade_level=11,
            evidence_code="mathematics",
            assessment_metrics={"net": 74},
        ),
    )

    assert report.action is ResponseValidationAction.REGENERATE
    assert [violation.rule_id for violation in report.violations] == [
        "CORE_MEMORY_CONTRADICTION",
        "CORE_UNKNOWN_FACT",
        "ASSESSMENT_UNKNOWN_RESULT",
    ]


def test_validate_response_rejects_regenerate_report_compatibly() -> None:
    with pytest.raises(ResponseValidationError) as captured:
        validate_response(
            "Sen 10. sınıftasın.",
            snapshot=make_contextual_snapshot(grade_level=11),
        )

    assert captured.value.violations == ["CORE_MEMORY_CONTRADICTION"]
    assert captured.value.report is not None
    assert captured.value.report.action is ResponseValidationAction.REGENERATE
