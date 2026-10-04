from educoach.rules.coach_rules import validate_coach_response
from educoach.rules.contracts import RuleSeverity, RuleViolation

from .contracts import ResponseValidationAction, ResponseValidationReport


class ResponseValidationError(ValueError):
    def __init__(
        self,
        violations: list[str],
        report: ResponseValidationReport | None = None,
    ) -> None:
        self.violations = violations
        self.report = report
        super().__init__(f"Coach response rejected: {', '.join(violations)}")


def evaluate_response(text: str) -> ResponseValidationReport:
    violations = tuple(
        RuleViolation(
            rule_id=violation,
            severity=RuleSeverity.ERROR,
            message=violation,
        )
        for violation in validate_coach_response(text)
    )
    action = (
        ResponseValidationAction.BLOCK
        if violations
        else ResponseValidationAction.PASS
    )
    return ResponseValidationReport(action=action, violations=violations)


def validate_response(text: str) -> str:
    report = evaluate_response(text)
    if report.action is ResponseValidationAction.BLOCK:
        violations = [violation.rule_id for violation in report.violations]
        raise ResponseValidationError(violations, report=report)
    return text.strip()


def validate_user_message(message: str) -> str:
    cleaned = message.strip()
    if not cleaned:
        raise ValueError("User message cannot be empty")
    if len(cleaned) > 12000:
        raise ValueError("User message is too long")
    return cleaned
