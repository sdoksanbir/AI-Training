from educoach.rules import validate_coach_response


class ResponseValidationError(ValueError):
    def __init__(self, violations: list[str]) -> None:
        self.violations = violations
        super().__init__(f"Coach response rejected: {', '.join(violations)}")


def validate_response(text: str) -> str:
    violations = validate_coach_response(text)
    if violations:
        raise ResponseValidationError(violations)
    return text.strip()
