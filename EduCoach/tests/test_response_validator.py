from dataclasses import FrozenInstanceError

import pytest

from educoach.rules.contracts import RuleSeverity, RuleViolation
from educoach.validators import (
    ResponseValidationAction,
    ResponseValidationError,
    evaluate_response,
    validate_response,
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
