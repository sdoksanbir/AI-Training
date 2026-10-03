def validate_coach_response(text: str) -> list[str]:
    """Returns deterministic violations that must block a response."""
    violations: list[str] = []
    if not text.strip():
        violations.append("empty_response")
    if len(text) > 12000:
        violations.append("response_too_long")
    return violations
