"""Runtime handling for already-evaluated response validation actions."""

from educoach.validators import (
    ResponseValidationAction,
    ResponseValidationError,
    ResponseValidationReport,
)


class ResponseRegenerationRequired(ResponseValidationError):
    """Signal that a rejected response requires controlled regeneration."""

    def __init__(self, report: ResponseValidationReport) -> None:
        _require_action(report, ResponseValidationAction.REGENERATE)
        super().__init__(_violation_ids(report), report=report)


class ResponseAutoFixRequired(ResponseValidationError):
    """Signal that a deterministic response fix is required but unavailable."""

    def __init__(self, report: ResponseValidationReport) -> None:
        _require_action(report, ResponseValidationAction.AUTO_FIX)
        super().__init__(_violation_ids(report), report=report)


def handle_response_validation_action(
    text: str,
    report: ResponseValidationReport,
) -> str:
    """Apply the action selected by the response evaluator without recomputing it."""
    if report.action is ResponseValidationAction.PASS:
        return text.strip()
    if report.action is ResponseValidationAction.BLOCK:
        raise ResponseValidationError(_violation_ids(report), report=report)
    if report.action is ResponseValidationAction.REGENERATE:
        raise ResponseRegenerationRequired(report)
    if report.action is ResponseValidationAction.AUTO_FIX:
        raise ResponseAutoFixRequired(report)
    raise RuntimeError(f"Unsupported response validation action: {report.action!r}")


def _require_action(
    report: ResponseValidationReport,
    expected: ResponseValidationAction,
) -> None:
    if not isinstance(report, ResponseValidationReport):
        raise ValueError("a response validation report is required")
    if report.action is not expected:
        raise ValueError(f"response validation report action must be {expected.value}")


def _violation_ids(report: ResponseValidationReport) -> list[str]:
    return [violation.rule_id for violation in report.violations]
