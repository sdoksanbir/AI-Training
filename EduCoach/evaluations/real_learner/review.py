"""Content-free aggregation for manually completed development reviews."""

from collections import Counter, defaultdict
from collections.abc import Iterable
import json
from pathlib import Path
import re

from pydantic import BaseModel, ConfigDict, Field, StrictFloat, StrictInt, StrictStr

from .contracts import RealLearnerEvaluationCase
from .coverage import (
    CoverageFamilyId,
    DevelopmentCoverageContract,
    RequiredProgramCode,
)
from .runner import (
    DevelopmentCaseResult,
    DevelopmentRunSummary,
    ExecutionStatus,
    HumanReviewRecord,
)


SAFE_FALLBACK_ACCEPTABLE = "SAFE_FALLBACK_ACCEPTABLE"
SAFE_FALLBACK_LOW_UTILITY = "SAFE_FALLBACK_LOW_UTILITY"


class ReviewArtifactError(ValueError):
    """Safe review artifact error that never contains private content."""


class ExpectedReviewCounts(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    met: StrictInt = Field(ge=0)
    not_met: StrictInt = Field(ge=0)
    unclear: StrictInt = Field(ge=0)
    unreviewed: StrictInt = Field(ge=0)


class ForbiddenReviewCounts(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    absent: StrictInt = Field(ge=0)
    present: StrictInt = Field(ge=0)
    unclear: StrictInt = Field(ge=0)
    unreviewed: StrictInt = Field(ge=0)


class FallbackReviewCounts(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    fallback_count: StrictInt = Field(ge=0)
    acceptable: StrictInt = Field(ge=0)
    low_utility: StrictInt = Field(ge=0)
    unreviewed_or_invalid: StrictInt = Field(ge=0)


class FamilyProgramReviewSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    family_id: CoverageFamilyId
    program_code: RequiredProgramCode
    completed_count: StrictInt = Field(ge=0)
    reviewed_count: StrictInt = Field(ge=0)
    unreviewed_count: StrictInt = Field(ge=0)


class HumanReviewSummary(BaseModel):
    """Aggregate-only summary; no case IDs, messages, facts, or responses."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: StrictStr
    completed_count: StrictInt = Field(ge=0)
    reviewed_count: StrictInt = Field(ge=0)
    incomplete_review_count: StrictInt = Field(ge=0)
    expected_review: ExpectedReviewCounts
    forbidden_review: ForbiddenReviewCounts
    fallback: FallbackReviewCounts
    fallback_rate: StrictFloat = Field(ge=0.0, le=1.0)
    proposal_count: StrictInt = Field(ge=0)
    proposal_review_presence_count: StrictInt = Field(ge=0)
    family_program: tuple[FamilyProgramReviewSummary, ...]


def load_development_results(path: Path) -> tuple[DevelopmentCaseResult, ...]:
    return _load_jsonl(path, DevelopmentCaseResult, "development results")


def load_human_reviews(path: Path) -> tuple[HumanReviewRecord, ...]:
    return _load_jsonl(path, HumanReviewRecord, "human review")


def load_development_run_summary(path: Path) -> DevelopmentRunSummary:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return DevelopmentRunSummary.model_validate(payload)
    except Exception as error:
        raise ReviewArtifactError("development run summary is invalid") from error


def summarize_human_reviews(
    contract: DevelopmentCoverageContract,
    cases: Iterable[RealLearnerEvaluationCase],
    results: Iterable[DevelopmentCaseResult],
    reviews: Iterable[HumanReviewRecord],
    *,
    run_id: str,
) -> HumanReviewSummary:
    """Count explicit human decisions without inferring or scoring them."""

    case_tuple = tuple(cases)
    result_tuple = tuple(results)
    review_tuple = tuple(reviews)
    case_by_id = _unique_index(case_tuple, "case")
    result_by_id = _unique_index(result_tuple, "result")
    review_by_id = _unique_index(review_tuple, "review")
    if set(result_by_id) != set(review_by_id):
        raise ReviewArtifactError("result and review case sets must match")
    if not set(result_by_id).issubset(case_by_id):
        raise ReviewArtifactError("result case set must belong to development input")

    completed_ids = {
        case_id
        for case_id, result in result_by_id.items()
        if result.execution_status is ExecutionStatus.COMPLETED
    }
    complete_review_ids = {
        case_id
        for case_id in completed_ids
        if _review_is_complete(review_by_id[case_id])
    }
    expected = Counter(
        review_by_id[case_id].expected_review or "unreviewed"
        for case_id in completed_ids
    )
    forbidden = Counter(
        review_by_id[case_id].forbidden_review or "unreviewed"
        for case_id in completed_ids
    )

    fallback_ids = {
        case_id
        for case_id in completed_ids
        if result_by_id[case_id].runtime_metadata.model == "deterministic"
    }
    acceptable = 0
    low_utility = 0
    unreviewed_or_invalid = 0
    for case_id in fallback_ids:
        classification = _fallback_classification(review_by_id[case_id].notes)
        if classification == SAFE_FALLBACK_ACCEPTABLE:
            acceptable += 1
        elif classification == SAFE_FALLBACK_LOW_UTILITY:
            low_utility += 1
        else:
            unreviewed_or_invalid += 1

    proposal_ids = {
        case_id
        for case_id in completed_ids
        if result_by_id[case_id].proposal_present
    }
    family_program = _family_program_summaries(
        contract,
        case_tuple,
        result_by_id,
        review_by_id,
    )
    completed_count = len(completed_ids)
    return HumanReviewSummary(
        run_id=run_id,
        completed_count=completed_count,
        reviewed_count=len(complete_review_ids),
        incomplete_review_count=completed_count - len(complete_review_ids),
        expected_review=ExpectedReviewCounts(
            met=expected["met"],
            not_met=expected["not_met"],
            unclear=expected["unclear"],
            unreviewed=expected["unreviewed"],
        ),
        forbidden_review=ForbiddenReviewCounts(
            absent=forbidden["absent"],
            present=forbidden["present"],
            unclear=forbidden["unclear"],
            unreviewed=forbidden["unreviewed"],
        ),
        fallback=FallbackReviewCounts(
            fallback_count=len(fallback_ids),
            acceptable=acceptable,
            low_utility=low_utility,
            unreviewed_or_invalid=unreviewed_or_invalid,
        ),
        fallback_rate=(len(fallback_ids) / completed_count if completed_count else 0.0),
        proposal_count=len(proposal_ids),
        proposal_review_presence_count=sum(
            review_by_id[case_id].proposal_review is not None
            for case_id in proposal_ids
        ),
        family_program=family_program,
    )


def write_private_aggregate(path: Path, model: BaseModel) -> None:
    """Write or refresh a derived aggregate beside private run artifacts."""

    content = json.dumps(
        model.model_dump(mode="json"),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"
    path.write_text(content, encoding="utf-8", newline="\n")


def _load_jsonl(path: Path, model_type, label: str):
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        raise ReviewArtifactError(f"{label} artifact could not be read") from error
    records = []
    for line_number, line in enumerate(lines, start=1):
        try:
            payload = json.loads(line)
            records.append(model_type.model_validate(payload))
        except Exception as error:
            raise ReviewArtifactError(
                f"{label} artifact is invalid at line {line_number}"
            ) from error
    return tuple(records)


def _unique_index(items, label: str) -> dict[str, object]:
    indexed: dict[str, object] = {}
    for item in items:
        if item.case_id in indexed:
            raise ReviewArtifactError(f"duplicate {label} case ID")
        indexed[item.case_id] = item
    return indexed


def _review_is_complete(review: HumanReviewRecord) -> bool:
    return (
        review.expected_review is not None
        and review.forbidden_review is not None
        and review.notes is not None
        and bool(review.notes.strip())
    )


def _fallback_classification(notes: str | None) -> str | None:
    if not notes:
        return None
    found = {
        term
        for term in (SAFE_FALLBACK_ACCEPTABLE, SAFE_FALLBACK_LOW_UTILITY)
        if re.search(rf"(?<![A-Z_]){term}(?![A-Z_])", notes)
    }
    return next(iter(found)) if len(found) == 1 else None


def _family_program_summaries(
    contract: DevelopmentCoverageContract,
    cases: tuple[RealLearnerEvaluationCase, ...],
    result_by_id: dict[str, DevelopmentCaseResult],
    review_by_id: dict[str, HumanReviewRecord],
) -> tuple[FamilyProgramReviewSummary, ...]:
    grouped: dict[tuple[str, str], list[RealLearnerEvaluationCase]] = defaultdict(list)
    for case in cases:
        grouped[(case.program_code, case.source_group_id)].append(case)

    summaries = []
    for family in sorted(contract.required_families, key=lambda item: item.family_id):
        for program_code in family.required_program_codes:
            candidates = tuple(
                case
                for case in cases
                if case.program_code == program_code
                and _case_represents_family(family, case, grouped, result_by_id)
            )
            completed_ids = {
                case.case_id
                for case in candidates
                if case.case_id in result_by_id
                and result_by_id[case.case_id].execution_status
                is ExecutionStatus.COMPLETED
            }
            reviewed_count = sum(
                _review_is_complete(review_by_id[case_id])
                for case_id in completed_ids
            )
            summaries.append(
                FamilyProgramReviewSummary(
                    family_id=family.family_id,
                    program_code=program_code,
                    completed_count=len(completed_ids),
                    reviewed_count=reviewed_count,
                    unreviewed_count=len(completed_ids) - reviewed_count,
                )
            )
    return tuple(summaries)


def _case_represents_family(family, case, grouped, result_by_id) -> bool:
    expectation = family.minimum_expectation
    if expectation == "one_completed_deterministic_fallback_case_per_required_program":
        result = result_by_id.get(case.case_id)
        return result is not None and result.runtime_metadata.model == "deterministic"
    if expectation == "one_completed_multi_case_source_group_per_required_program":
        return len(grouped[(case.program_code, case.source_group_id)]) >= 2
    tags = set(case.expected_behavior_tags) | set(case.forbidden_behavior_tags)
    return bool(tags & set(family.coverage_tags))
