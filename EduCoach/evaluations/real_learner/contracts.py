"""Strict evaluation-only contracts for privacy-reviewed learner cases."""

from collections.abc import Iterable
import json
from pathlib import Path
import re
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictFloat,
    StrictInt,
    StrictStr,
    StringConstraints,
    ValidationError,
    field_validator,
    model_validator,
)


CaseId = Annotated[
    StrictStr,
    StringConstraints(pattern=r"^RL[0-9]{4,}$"),
]
SourceGroupId = Annotated[
    StrictStr,
    StringConstraints(pattern=r"^RG[0-9]{4,}$"),
]
ControlledName = Annotated[
    StrictStr,
    StringConstraints(pattern=r"^[a-z][a-z0-9_]{0,63}$"),
]
FactValue = StrictStr | StrictBool | StrictInt | StrictFloat
FactSource = Literal[
    "learner_reported",
    "teacher_reported",
    "parent_reported",
    "assessment_derived",
    "coach_inferred",
    "system_observed",
]


_EMAIL_PATTERN = re.compile(
    r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
    re.IGNORECASE,
)
_PHONE_PATTERN = re.compile(
    r"(?<!\w)\+?(?:\d[\s().-]*){9,14}\d(?!\w)"
)
_UUID_PATTERN = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-"
    r"[89ab][0-9a-f]{3}-[0-9a-f]{12}\b",
    re.IGNORECASE,
)
_TOKEN_PATTERN = re.compile(
    r"\b(?:bearer|access[_ -]?token|auth[_ -]?token|"
    r"session[_ -]?token|token)\s*(?::|=)?\s+"
    r"[A-Za-z0-9._~+/=-]{3,}\b",
    re.IGNORECASE,
)
_SOCIAL_HANDLE_PATTERN = re.compile(
    r"(?<![\w@])@[A-Za-z0-9_][A-Za-z0-9_.]{1,29}\b"
)


class SanitizedFact(BaseModel):
    """A deliberately flat fact safe for evaluation input."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: ControlledName
    value: FactValue
    source: FactSource


class RealLearnerEvaluationCase(BaseModel):
    """A manually anonymized and authorized evaluation-only case."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: CaseId
    source_group_id: SourceGroupId
    source_kind: Literal["real_anonymized"]
    category: ControlledName
    program_code: ControlledName
    user_message: StrictStr = Field(min_length=1, max_length=5000)
    facts: tuple[SanitizedFact, ...]
    expected_behavior_tags: tuple[ControlledName, ...] = Field(min_length=1)
    forbidden_behavior_tags: tuple[ControlledName, ...]
    privacy_reviewed: StrictBool
    usage_authorized: StrictBool

    @field_validator("user_message")
    @classmethod
    def reject_blank_message(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("user_message cannot be blank")
        return value

    @field_validator("expected_behavior_tags", "forbidden_behavior_tags")
    @classmethod
    def require_unique_tags(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("behavior tags must be unique")
        return tuple(sorted(value))

    @model_validator(mode="after")
    def enforce_review_and_privacy_guard(self) -> "RealLearnerEvaluationCase":
        if self.privacy_reviewed is not True:
            raise ValueError("privacy_reviewed must be true")
        if self.usage_authorized is not True:
            raise ValueError("usage_authorized must be true")

        findings = scan_case_for_likely_identifiers(self)
        if findings:
            raise ValueError(
                "likely identifier detected: " + ", ".join(findings)
            )
        return self


class CaseFileValidationError(ValueError):
    """Safe validation errors that never contain raw case content."""

    def __init__(self, errors: Iterable[str]) -> None:
        self.errors = tuple(errors)
        super().__init__("; ".join(self.errors))


def scan_case_for_likely_identifiers(
    case: RealLearnerEvaluationCase,
) -> tuple[str, ...]:
    """Flag obvious identifiers; this is not an anonymizer."""

    texts = [case.user_message]
    texts.extend(
        fact.value
        for fact in case.facts
        if isinstance(fact.value, str)
    )
    findings: set[str] = set()
    patterns = (
        ("email", _EMAIL_PATTERN),
        ("phone", _PHONE_PATTERN),
        ("uuid", _UUID_PATTERN),
        ("token", _TOKEN_PATTERN),
        ("social_handle", _SOCIAL_HANDLE_PATTERN),
    )
    for text in texts:
        for label, pattern in patterns:
            if pattern.search(text):
                findings.add(label)
    return tuple(sorted(findings))


def load_validated_cases(path: Path) -> tuple[RealLearnerEvaluationCase, ...]:
    """Load strict JSONL without echoing raw content on failure."""

    errors: list[str] = []
    cases: list[RealLearnerEvaluationCase] = []
    seen_case_ids: set[str] = set()
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        raise CaseFileValidationError(("input file could not be read",)) from error

    if not lines:
        raise CaseFileValidationError(("input file is empty",))

    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            errors.append(f"line {line_number}: blank JSONL line")
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            errors.append(f"line {line_number}: invalid JSON")
            continue
        try:
            case = RealLearnerEvaluationCase.model_validate(payload)
        except ValidationError as error:
            details = error.errors(include_input=False, include_url=False)
            locations = sorted(
                {
                    ".".join(str(item) for item in detail["loc"])
                    or "case"
                    for detail in details
                }
            )
            errors.append(
                f"line {line_number}: contract validation failed at "
                + ", ".join(locations)
            )
            continue

        if case.case_id in seen_case_ids:
            errors.append(f"line {line_number}: duplicate case_id")
            continue
        seen_case_ids.add(case.case_id)
        cases.append(case)

    if errors:
        raise CaseFileValidationError(errors)
    return tuple(cases)
