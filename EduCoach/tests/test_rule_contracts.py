from dataclasses import FrozenInstanceError

import pytest

from educoach.rules import RuleEvaluation, RuleSeverity, RuleViolation


def make_violation(
    rule_id: str = "PLAN_AVAILABLE_TIME_LIMIT",
    severity: RuleSeverity = RuleSeverity.ERROR,
    message: str = "Plan available time limit exceeded",
) -> RuleViolation:
    return RuleViolation(rule_id=rule_id, severity=severity, message=message)


def test_rule_severity_has_four_controlled_members() -> None:
    assert list(RuleSeverity) == [
        RuleSeverity.INFO,
        RuleSeverity.WARNING,
        RuleSeverity.ERROR,
        RuleSeverity.CRITICAL,
    ]


def test_rule_severity_uses_stable_string_values() -> None:
    assert [severity.value for severity in RuleSeverity] == [
        "info",
        "warning",
        "error",
        "critical",
    ]


def test_rule_violation_preserves_required_fields() -> None:
    violation = make_violation()

    assert violation.rule_id == "PLAN_AVAILABLE_TIME_LIMIT"
    assert violation.severity is RuleSeverity.ERROR
    assert violation.message == "Plan available time limit exceeded"


def test_rule_evaluation_supports_no_violations() -> None:
    assert RuleEvaluation().violations == ()


def test_rule_evaluation_supports_multiple_violations_in_order() -> None:
    warning = make_violation(
        rule_id="FIRST_RULE",
        severity=RuleSeverity.WARNING,
        message="First violation",
    )
    critical = make_violation(
        rule_id="SECOND_RULE",
        severity=RuleSeverity.CRITICAL,
        message="Second violation",
    )

    evaluation = RuleEvaluation(violations=(warning, critical))

    assert evaluation.violations == (warning, critical)


def test_rule_violation_is_immutable() -> None:
    violation = make_violation()

    with pytest.raises(FrozenInstanceError):
        violation.message = "Changed"


def test_rule_evaluation_and_its_collection_are_immutable() -> None:
    evaluation = RuleEvaluation(violations=(make_violation(),))

    assert isinstance(evaluation.violations, tuple)
    with pytest.raises(FrozenInstanceError):
        evaluation.violations = ()
