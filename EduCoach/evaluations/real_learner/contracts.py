"""Strict evaluation-only contracts for privacy-reviewed learner cases."""

from collections.abc import Iterable
from datetime import date
import json
from pathlib import Path
import re
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
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
_PUBLIC_URL_PATTERN = re.compile(
    r"(?:https?://|www\.)\S+",
    re.IGNORECASE,
)


class PublicForumProvenance(BaseModel):
    """Private collection metadata that never enters prompts or aggregates."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    platform_domain: StrictStr = Field(min_length=1, max_length=253)
    original_public_url: HttpUrl
    access_date: date
    policy_terms_reviewed: StrictBool

    @model_validator(mode="after")
    def require_reviewed_matching_source(self) -> "PublicForumProvenance":
        if self.policy_terms_reviewed is not True:
            raise ValueError("policy_terms_reviewed must be true")
        normalized_domain = (
            self.platform_domain.strip().lower().removeprefix("www.")
        )
        source_host = (self.original_public_url.host or "").lower().removeprefix("www.")
        if not normalized_domain or source_host != normalized_domain:
            raise ValueError("public source domain must match original_public_url")
        return self


class SanitizedFact(BaseModel):
    """A deliberately flat fact safe for evaluation input."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: ControlledName
    value: FactValue
    source: FactSource


class RealLearnerEvaluationCase(BaseModel):
    """A source-aware, manually minimized evaluation-only case."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: CaseId
    source_group_id: SourceGroupId
    source_kind: Literal["real_anonymized", "public_forum"]
    category: ControlledName
    program_code: ControlledName
    user_message: StrictStr = Field(min_length=1, max_length=5000)
    facts: tuple[SanitizedFact, ...]
    expected_behavior_tags: tuple[ControlledName, ...] = Field(min_length=1)
    forbidden_behavior_tags: tuple[ControlledName, ...]
    privacy_reviewed: StrictBool | None = None
    usage_authorized: StrictBool | None = None
    public_source_reviewed: StrictBool | None = None
    content_minimized: StrictBool | None = None
    evaluation_only: StrictBool | None = None
    public_provenance: PublicForumProvenance | None = None

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
        if self.source_kind == "real_anonymized":
            if self.privacy_reviewed is not True:
                raise ValueError("privacy_reviewed must be true")
            if self.usage_authorized is not True:
                raise ValueError("usage_authorized must be true")
            if any(
                value is not None
                for value in (
                    self.public_source_reviewed,
                    self.content_minimized,
                    self.evaluation_only,
                    self.public_provenance,
                )
            ):
                raise ValueError(
                    "public forum assertions do not apply to real_anonymized"
                )
        else:
            if (
                self.privacy_reviewed is not None
                or self.usage_authorized is not None
            ):
                raise ValueError(
                    "public_forum cannot use real_anonymized assertions"
                )
            if self.public_source_reviewed is not True:
                raise ValueError("public_source_reviewed must be true")
            if self.content_minimized is not True:
                raise ValueError("content_minimized must be true")
            if self.evaluation_only is not True:
                raise ValueError("evaluation_only must be true")
            if self.public_provenance is None:
                raise ValueError("public_provenance is required")

        findings = scan_case_for_likely_identifiers(self)
        if self.source_kind == "public_forum":
            findings = tuple(
                sorted(set(findings) | set(_public_source_content_findings(self)))
            )
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


class PublicForumSourceGroupError(ValueError):
    """Raised when public forum cases would enable cross-post identity linking."""


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


def require_case_local_public_forum_groups(
    cases: Iterable[RealLearnerEvaluationCase],
) -> None:
    """Require every public forum source group to represent exactly one case."""

    case_tuple = tuple(cases)
    group_counts: dict[str, int] = {}
    public_groups: set[str] = set()
    for case in case_tuple:
        group_counts[case.source_group_id] = (
            group_counts.get(case.source_group_id, 0) + 1
        )
        if case.source_kind == "public_forum":
            public_groups.add(case.source_group_id)
    if any(group_counts[group_id] != 1 for group_id in public_groups):
        raise PublicForumSourceGroupError(
            "public_forum source_group_id must be case-local"
        )


def _public_source_content_findings(
    case: RealLearnerEvaluationCase,
) -> tuple[str, ...]:
    texts = [case.user_message]
    texts.extend(
        fact.value for fact in case.facts if isinstance(fact.value, str)
    )
    findings: set[str] = set()
    domain = (
        case.public_provenance.platform_domain.strip().lower()
        if case.public_provenance is not None
        else ""
    )
    for text in texts:
        if _PUBLIC_URL_PATTERN.search(text):
            findings.add("public_url")
        if domain and domain in text.lower():
            findings.add("public_source_domain")
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
    try:
        require_case_local_public_forum_groups(cases)
    except PublicForumSourceGroupError as error:
        raise CaseFileValidationError((str(error),)) from error
    return tuple(cases)
