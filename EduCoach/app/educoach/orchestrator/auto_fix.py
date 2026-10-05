"""Bounded deterministic response auto-fix policies."""

from educoach.validators import ResponseValidationAction, ResponseValidationReport
from educoach.validators.repetition import (
    repetition_duplicate_segment_indexes,
    segment_response,
)

from .response_actions import ResponseAutoFixRequired


SUPPORTED_AUTO_FIX_RULE_IDS = frozenset({"OUTPUT_REPETITION_LOOP"})


def apply_response_auto_fix(
    text: str,
    report: ResponseValidationReport,
) -> str:
    """Apply one supported deterministic fix without selecting an action."""
    if not isinstance(report, ResponseValidationReport):
        raise ValueError("a response validation report is required")
    if report.action is not ResponseValidationAction.AUTO_FIX:
        raise ValueError("response validation report action must be auto_fix")

    rule_ids = frozenset(violation.rule_id for violation in report.violations)
    if not rule_ids or not rule_ids.issubset(SUPPORTED_AUTO_FIX_RULE_IDS):
        raise ResponseAutoFixRequired(report)

    duplicate_indexes = repetition_duplicate_segment_indexes(text)
    if not duplicate_indexes:
        raise ResponseAutoFixRequired(report)
    return "".join(
        segment.render()
        for index, segment in enumerate(segment_response(text))
        if index not in duplicate_indexes
    )
