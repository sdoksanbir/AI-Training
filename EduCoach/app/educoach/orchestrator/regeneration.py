"""Bounded request construction for controlled response regeneration."""

from educoach.llm import LLMRequest
from educoach.validators import ResponseValidationAction, ResponseValidationReport

from .response_actions import ResponseRegenerationRequired


MAX_REGENERATION_ATTEMPTS = 1


class ResponseRegenerationExhausted(ResponseRegenerationRequired):
    """Signal that all allowed controlled regeneration attempts were used."""


def build_regeneration_request(
    original_request: LLMRequest,
    report: ResponseValidationReport,
) -> LLMRequest:
    """Append authoritative validation feedback without changing user context."""
    if not isinstance(report, ResponseValidationReport):
        raise ValueError("a response validation report is required")
    if report.action is not ResponseValidationAction.REGENERATE:
        raise ValueError("response validation report action must be regenerate")

    violation_feedback = "\n".join(
        f"- {violation.rule_id}: {violation.message}"
        for violation in report.violations
    )
    regeneration_instruction = (
        "Previous response failed response validation.\n\n"
        "Correct all of these backend validation violations:\n"
        f"{violation_feedback}\n\n"
        "Generate the answer again.\n"
        "Do not mention validator internals, rule IDs, or this correction "
        "process to the user.\n"
        "Preserve every original system instruction and required output format."
    )
    return LLMRequest(
        system_prompt=(
            f"{original_request.system_prompt}\n\n{regeneration_instruction}"
        ),
        user_message=original_request.user_message,
        memory_context=original_request.memory_context,
    )
