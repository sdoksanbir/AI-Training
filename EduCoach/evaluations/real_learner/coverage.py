"""Versioned, privacy-safe development coverage evaluation contracts."""

from collections import Counter, defaultdict
from collections.abc import Iterable
from enum import StrEnum
import json
from pathlib import Path
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictStr,
    StringConstraints,
    ValidationError,
    field_validator,
    model_validator,
)

from .contracts import RealLearnerEvaluationCase
from .runner import DevelopmentCaseResult, ExecutionStatus


COVERAGE_CONTRACT_VERSION = "faz12-development-coverage-v0.1"
DEFAULT_COVERAGE_CONTRACT_PATH = (
    Path(__file__).resolve().parent / "development_coverage_v0.1.json"
)

RequiredProgramCode = Literal["school_7", "yks"]
OutOfScopeProgramCode = Literal["lgs"]
CoveragePriority = Literal["P0", "P1"]
CoverageFamilyId = Literal[
    "availability_grounding",
    "clarification_unknown_context",
    "deterministic_safe_fallback",
    "exam_analysis",
    "goal_pressure_realism",
    "low_study_tolerance",
    "multi_case_source_group",
    "parent_reporter",
    "planning_constraints",
    "school_exam_balance",
    "structured_plan_proposal",
    "unknown_fact_grounding",
]
MinimumExpectation = Literal[
    "one_completed_case_per_required_program",
    "one_completed_deterministic_fallback_case_per_required_program",
    "one_completed_multi_case_source_group_per_required_program",
    "one_completed_proposal_case_per_required_program",
]
CoverageTag = Annotated[
    StrictStr,
    StringConstraints(pattern=r"^[a-z][a-z0-9_]{0,63}$"),
]

REQUIRED_PROGRAM_CODES = frozenset({"school_7", "yks"})
OUT_OF_SCOPE_PROGRAM_CODES = frozenset({"lgs"})
REQUIRED_FAMILY_IDS = frozenset(CoverageFamilyId.__args__)


class CoverageContractError(ValueError):
    """Raised without echoing arbitrary manifest content."""


class FinalUnseenIsolationError(ValueError):
    """Raised when development and final cases share a source group."""


class CoverageStatus(StrEnum):
    COVERED = "COVERED"
    PARTIAL = "PARTIAL"
    MISSING = "MISSING"


class DevelopmentCoverageFamily(BaseModel):
    """One required behavior family in the FAZ 12 development scope."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    family_id: CoverageFamilyId
    description: StrictStr = Field(min_length=1, max_length=500)
    required_program_codes: tuple[RequiredProgramCode, ...] = Field(min_length=1)
    coverage_tags: tuple[CoverageTag, ...]
    priority: CoveragePriority
    minimum_expectation: MinimumExpectation

    @field_validator("required_program_codes", "coverage_tags")
    @classmethod
    def require_unique_sorted_values(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("coverage family values must be unique")
        return tuple(sorted(value))

    @model_validator(mode="after")
    def validate_expectation_shape(self) -> "DevelopmentCoverageFamily":
        tag_based = {
            "one_completed_case_per_required_program",
            "one_completed_proposal_case_per_required_program",
        }
        if self.minimum_expectation in tag_based and not self.coverage_tags:
            raise ValueError("tag-based coverage families require coverage_tags")
        if self.minimum_expectation not in tag_based and self.coverage_tags:
            raise ValueError("structural/runtime coverage families cannot use tags")
        return self


class DevelopmentCoverageContract(BaseModel):
    """Strict versioned taxonomy; never stores learner or model content."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    version: Literal["faz12-development-coverage-v0.1"]
    required_program_codes: tuple[RequiredProgramCode, ...]
    out_of_scope_program_codes: tuple[OutOfScopeProgramCode, ...]
    required_families: tuple[DevelopmentCoverageFamily, ...]

    @field_validator("required_program_codes", "out_of_scope_program_codes")
    @classmethod
    def require_unique_sorted_programs(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("program codes must be unique")
        return tuple(sorted(value))

    @model_validator(mode="after")
    def enforce_v0_1_scope(self) -> "DevelopmentCoverageContract":
        if set(self.required_program_codes) != REQUIRED_PROGRAM_CODES:
            raise ValueError("v0.1 required program scope must be exact")
        if set(self.out_of_scope_program_codes) != OUT_OF_SCOPE_PROGRAM_CODES:
            raise ValueError("v0.1 out-of-scope program set must be exact")

        family_ids = [family.family_id for family in self.required_families]
        if len(family_ids) != len(set(family_ids)):
            raise ValueError("coverage family IDs must be unique")
        if set(family_ids) != REQUIRED_FAMILY_IDS:
            raise ValueError("v0.1 required family set must be exact")
        return self


class ProgramFamilyCoverage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    program_code: RequiredProgramCode
    status: CoverageStatus


class FamilyCoverageResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    family_id: CoverageFamilyId
    priority: CoveragePriority
    status: CoverageStatus
    programs: tuple[ProgramFamilyCoverage, ...]


class ProgramCoverageResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    program_code: RequiredProgramCode
    status: CoverageStatus
    covered_family_ids: tuple[CoverageFamilyId, ...]
    open_family_ids: tuple[CoverageFamilyId, ...]


class OpenCoverageSlot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    program_code: RequiredProgramCode
    family_id: CoverageFamilyId
    status: Literal[CoverageStatus.PARTIAL, CoverageStatus.MISSING]


class DevelopmentCoverageReport(BaseModel):
    """Content-free aggregate report over private development evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    version: Literal["faz12-development-coverage-v0.1"]
    families: tuple[FamilyCoverageResult, ...]
    programs: tuple[ProgramCoverageResult, ...]
    open_slots: tuple[OpenCoverageSlot, ...]
    out_of_scope_program_codes_seen: tuple[StrictStr, ...]
    unscoped_program_codes_seen: tuple[StrictStr, ...]


def load_development_coverage_contract(
    path: Path = DEFAULT_COVERAGE_CONTRACT_PATH,
) -> DevelopmentCoverageContract:
    """Load the strict coverage taxonomy without exposing invalid content."""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return DevelopmentCoverageContract.model_validate(payload)
    except (OSError, UnicodeError, json.JSONDecodeError, ValidationError) as error:
        raise CoverageContractError("development coverage contract is invalid") from error


def evaluate_development_coverage(
    contract: DevelopmentCoverageContract,
    development_cases: Iterable[RealLearnerEvaluationCase],
    results: Iterable[DevelopmentCaseResult] = (),
    *,
    final_cases: Iterable[RealLearnerEvaluationCase] = (),
) -> DevelopmentCoverageReport:
    """Evaluate only controlled metadata and aggregate runtime evidence."""

    cases = tuple(development_cases)
    final = tuple(final_cases)
    _require_unique_case_ids(cases)
    _require_source_group_isolation(cases, final)
    result_by_case_id = _index_results(cases, tuple(results))

    family_results = tuple(
        _evaluate_family(family, cases, result_by_case_id)
        for family in sorted(
            contract.required_families,
            key=lambda item: item.family_id,
        )
    )
    program_results = tuple(
        _evaluate_program(program_code, family_results)
        for program_code in contract.required_program_codes
    )
    open_slots = tuple(
        OpenCoverageSlot(
            program_code=program.program_code,
            family_id=family.family_id,
            status=program.status,
        )
        for family in family_results
        for program in family.programs
        if program.status is not CoverageStatus.COVERED
    )
    seen_programs = {case.program_code for case in cases}
    return DevelopmentCoverageReport(
        version=contract.version,
        families=family_results,
        programs=program_results,
        open_slots=open_slots,
        out_of_scope_program_codes_seen=tuple(
            sorted(seen_programs & set(contract.out_of_scope_program_codes))
        ),
        unscoped_program_codes_seen=tuple(
            sorted(
                seen_programs
                - set(contract.required_program_codes)
                - set(contract.out_of_scope_program_codes)
            )
        ),
    )


def _evaluate_family(
    family: DevelopmentCoverageFamily,
    cases: tuple[RealLearnerEvaluationCase, ...],
    result_by_case_id: dict[str, DevelopmentCaseResult],
) -> FamilyCoverageResult:
    program_results = tuple(
        ProgramFamilyCoverage(
            program_code=program_code,
            status=_evaluate_family_program(
                family,
                program_code,
                cases,
                result_by_case_id,
            ),
        )
        for program_code in family.required_program_codes
    )
    statuses = {item.status for item in program_results}
    if statuses == {CoverageStatus.COVERED}:
        status = CoverageStatus.COVERED
    elif statuses == {CoverageStatus.MISSING}:
        status = CoverageStatus.MISSING
    else:
        status = CoverageStatus.PARTIAL
    return FamilyCoverageResult(
        family_id=family.family_id,
        priority=family.priority,
        status=status,
        programs=program_results,
    )


def _evaluate_family_program(
    family: DevelopmentCoverageFamily,
    program_code: RequiredProgramCode,
    cases: tuple[RealLearnerEvaluationCase, ...],
    result_by_case_id: dict[str, DevelopmentCaseResult],
) -> CoverageStatus:
    program_cases = tuple(
        case for case in cases if case.program_code == program_code
    )
    expectation = family.minimum_expectation

    if expectation == "one_completed_multi_case_source_group_per_required_program":
        grouped: dict[str, list[RealLearnerEvaluationCase]] = defaultdict(list)
        for case in program_cases:
            grouped[case.source_group_id].append(case)
        candidate_groups = tuple(
            group_cases for group_cases in grouped.values() if len(group_cases) >= 2
        )
        if any(
            sum(
                _is_completed(result_by_case_id.get(case.case_id))
                for case in group_cases
            )
            >= 2
            for group_cases in candidate_groups
        ):
            return CoverageStatus.COVERED
        return CoverageStatus.PARTIAL if candidate_groups else CoverageStatus.MISSING

    if expectation == "one_completed_deterministic_fallback_case_per_required_program":
        if any(
            _is_completed(result_by_case_id.get(case.case_id))
            and result_by_case_id[case.case_id].runtime_metadata.model
            == "deterministic"
            for case in program_cases
        ):
            return CoverageStatus.COVERED
        return CoverageStatus.PARTIAL if program_cases else CoverageStatus.MISSING

    family_tags = set(family.coverage_tags)
    candidates = tuple(
        case
        for case in program_cases
        if family_tags
        & (set(case.expected_behavior_tags) | set(case.forbidden_behavior_tags))
    )
    if expectation == "one_completed_proposal_case_per_required_program":
        if any(
            _is_completed(result_by_case_id.get(case.case_id))
            and result_by_case_id[case.case_id].proposal_present
            for case in candidates
        ):
            return CoverageStatus.COVERED
        return CoverageStatus.PARTIAL if candidates else CoverageStatus.MISSING

    if any(
        _is_completed(result_by_case_id.get(case.case_id)) for case in candidates
    ):
        return CoverageStatus.COVERED
    return CoverageStatus.PARTIAL if candidates else CoverageStatus.MISSING


def _evaluate_program(
    program_code: RequiredProgramCode,
    family_results: tuple[FamilyCoverageResult, ...],
) -> ProgramCoverageResult:
    relevant = tuple(
        (family.family_id, program.status)
        for family in family_results
        for program in family.programs
        if program.program_code == program_code
    )
    covered = tuple(
        family_id
        for family_id, status in relevant
        if status is CoverageStatus.COVERED
    )
    open_families = tuple(
        family_id
        for family_id, status in relevant
        if status is not CoverageStatus.COVERED
    )
    if not open_families:
        status = CoverageStatus.COVERED
    elif not covered and all(
        item_status is CoverageStatus.MISSING for _, item_status in relevant
    ):
        status = CoverageStatus.MISSING
    else:
        status = CoverageStatus.PARTIAL
    return ProgramCoverageResult(
        program_code=program_code,
        status=status,
        covered_family_ids=covered,
        open_family_ids=open_families,
    )


def _require_unique_case_ids(
    cases: tuple[RealLearnerEvaluationCase, ...],
) -> None:
    counts = Counter(case.case_id for case in cases)
    if any(count > 1 for count in counts.values()):
        raise ValueError("development coverage cases must have unique case IDs")


def _require_source_group_isolation(
    development_cases: tuple[RealLearnerEvaluationCase, ...],
    final_cases: tuple[RealLearnerEvaluationCase, ...],
) -> None:
    development_groups = {case.source_group_id for case in development_cases}
    final_groups = {case.source_group_id for case in final_cases}
    if development_groups & final_groups:
        raise FinalUnseenIsolationError(
            "development and final source groups must be disjoint"
        )


def _index_results(
    cases: tuple[RealLearnerEvaluationCase, ...],
    results: tuple[DevelopmentCaseResult, ...],
) -> dict[str, DevelopmentCaseResult]:
    result_ids = [result.case_id for result in results]
    if len(result_ids) != len(set(result_ids)):
        raise ValueError("development coverage results must have unique case IDs")
    case_ids = {case.case_id for case in cases}
    if not set(result_ids).issubset(case_ids):
        raise ValueError("development coverage result has no matching case")
    return {result.case_id: result for result in results}


def _is_completed(result: DevelopmentCaseResult | None) -> bool:
    return result is not None and result.execution_status is ExecutionStatus.COMPLETED
