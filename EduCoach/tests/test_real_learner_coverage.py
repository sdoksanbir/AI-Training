"""Synthetic shape fixtures for the FAZ 12.1 coverage contract."""

import json
from pathlib import Path

import pytest

from evaluations.real_learner import (
    DEFAULT_COVERAGE_CONTRACT_PATH,
    CoverageContractError,
    CoverageStatus,
    DevelopmentCaseResult,
    ExecutionStatus,
    FinalUnseenIsolationError,
    RealLearnerEvaluationCase,
    RuntimeMetadata,
    evaluate_development_coverage,
    load_development_coverage_contract,
    split_cases,
)


def synthetic_contract_case(
    index: int,
    *,
    program_code: str = "yks",
    group_index: int | None = None,
    expected_tags: tuple[str, ...] = ("recommend_exam_analysis",),
    forbidden_tags: tuple[str, ...] = (),
    message: str = "Synthetic contract fixture; not learner data.",
) -> RealLearnerEvaluationCase:
    return RealLearnerEvaluationCase.model_validate(
        {
            "case_id": f"RL{index:04d}",
            "source_group_id": f"RG{group_index or index:04d}",
            "source_kind": "real_anonymized",
            "category": "contract_fixture",
            "program_code": program_code,
            "user_message": message,
            "facts": [],
            "expected_behavior_tags": list(expected_tags),
            "forbidden_behavior_tags": list(forbidden_tags),
            "privacy_reviewed": True,
            "usage_authorized": True,
        }
    )


def synthetic_public_forum_case(
    index: int,
    *,
    program_code: str = "yks",
    expected_tags: tuple[str, ...] = ("recommend_exam_analysis",),
    forbidden_tags: tuple[str, ...] = (),
) -> RealLearnerEvaluationCase:
    return RealLearnerEvaluationCase.model_validate(
        {
            "case_id": f"RL{index:04d}",
            "source_group_id": f"RG{index:04d}",
            "source_kind": "public_forum",
            "category": "contract_fixture",
            "program_code": program_code,
            "user_message": "Manually paraphrased public discussion fixture.",
            "facts": [],
            "expected_behavior_tags": list(expected_tags),
            "forbidden_behavior_tags": list(forbidden_tags),
            "public_source_reviewed": True,
            "content_minimized": True,
            "evaluation_only": True,
            "public_provenance": {
                "platform_domain": "community.example.test",
                "original_public_url": (
                    f"https://community.example.test/thread/{index}"
                ),
                "access_date": "2026-10-07",
                "policy_terms_reviewed": True,
            },
        }
    )


def completed_result(
    case: RealLearnerEvaluationCase,
    *,
    model: str = "test-model",
    proposal_present: bool = False,
    response_text: str = "Synthetic result fixture; not learner data.",
) -> DevelopmentCaseResult:
    return DevelopmentCaseResult(
        case_id=case.case_id,
        source_group_id=case.source_group_id,
        execution_status=ExecutionStatus.COMPLETED,
        response_text=response_text,
        proposal_present=proposal_present,
        runtime_metadata=RuntimeMetadata(
            model=model,
            program_code=case.program_code,
        ),
    )


def write_contract(path: Path, payload: dict[str, object]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )


def family_status(report, family_id: str) -> CoverageStatus:
    return next(
        family.status
        for family in report.families
        if family.family_id == family_id
    )


def program_status(report, program_code: str) -> CoverageStatus:
    return next(
        program.status
        for program in report.programs
        if program.program_code == program_code
    )


def test_versioned_coverage_manifest_strictly_parses() -> None:
    contract = load_development_coverage_contract()

    assert contract.version == "faz12-development-coverage-v0.1"
    assert contract.required_program_codes == ("school_7", "yks")
    assert contract.out_of_scope_program_codes == ("lgs",)
    assert len(contract.required_families) == 12


def test_unknown_family_is_rejected(tmp_path: Path) -> None:
    payload = json.loads(DEFAULT_COVERAGE_CONTRACT_PATH.read_text(encoding="utf-8"))
    payload["required_families"][0]["family_id"] = "unknown_family"
    path = tmp_path / "unknown-family.json"
    write_contract(path, payload)

    with pytest.raises(CoverageContractError, match="contract is invalid"):
        load_development_coverage_contract(path)


@pytest.mark.parametrize("program_code", ["kpss", "lgs"])
def test_unknown_or_out_of_scope_program_cannot_be_required(
    tmp_path: Path,
    program_code: str,
) -> None:
    payload = json.loads(DEFAULT_COVERAGE_CONTRACT_PATH.read_text(encoding="utf-8"))
    payload["required_program_codes"].append(program_code)
    path = tmp_path / "unknown-program.json"
    write_contract(path, payload)

    with pytest.raises(CoverageContractError, match="contract is invalid"):
        load_development_coverage_contract(path)


def test_duplicate_family_is_rejected(tmp_path: Path) -> None:
    payload = json.loads(DEFAULT_COVERAGE_CONTRACT_PATH.read_text(encoding="utf-8"))
    payload["required_families"].append(payload["required_families"][0])
    path = tmp_path / "duplicate-family.json"
    write_contract(path, payload)

    with pytest.raises(CoverageContractError, match="contract is invalid"):
        load_development_coverage_contract(path)


def test_completed_required_family_is_covered() -> None:
    contract = load_development_coverage_contract()
    case = synthetic_contract_case(1)

    report = evaluate_development_coverage(
        contract,
        (case,),
        (completed_result(case),),
    )

    assert family_status(report, "exam_analysis") is CoverageStatus.COVERED


def test_public_forum_can_cover_normal_development_family() -> None:
    contract = load_development_coverage_contract()
    case = synthetic_public_forum_case(1)

    report = evaluate_development_coverage(
        contract,
        (case,),
        (completed_result(case),),
    )

    assert family_status(report, "exam_analysis") is CoverageStatus.COVERED


def test_missing_family_and_program_are_reported() -> None:
    contract = load_development_coverage_contract()
    case = synthetic_contract_case(1)

    report = evaluate_development_coverage(
        contract,
        (case,),
        (completed_result(case),),
    )

    assert family_status(report, "parent_reporter") is CoverageStatus.MISSING
    assert program_status(report, "yks") is CoverageStatus.PARTIAL
    assert program_status(report, "school_7") is CoverageStatus.MISSING
    assert any(
        slot.program_code == "school_7"
        and slot.family_id == "parent_reporter"
        and slot.status is CoverageStatus.MISSING
        for slot in report.open_slots
    )


def test_lgs_is_visible_but_outside_faz12_v0_1_scope() -> None:
    contract = load_development_coverage_contract()
    lgs_case = synthetic_contract_case(1, program_code="lgs")

    report = evaluate_development_coverage(contract, (lgs_case,))

    assert report.out_of_scope_program_codes_seen == ("lgs",)
    assert program_status(report, "yks") is CoverageStatus.MISSING
    assert program_status(report, "school_7") is CoverageStatus.MISSING


def test_proposal_and_fallback_have_separate_quality_evidence() -> None:
    contract = load_development_coverage_contract()
    proposal_case = synthetic_contract_case(
        1,
        expected_tags=("build_weekly_plan",),
    )
    fallback_case = synthetic_contract_case(
        2,
        expected_tags=("build_sustainable_plan",),
    )

    without_proposal = evaluate_development_coverage(
        contract,
        (proposal_case, fallback_case),
        (
            completed_result(proposal_case),
            completed_result(fallback_case, model="deterministic"),
        ),
    )
    with_proposal = evaluate_development_coverage(
        contract,
        (proposal_case, fallback_case),
        (
            completed_result(proposal_case, proposal_present=True),
            completed_result(fallback_case, model="deterministic"),
        ),
    )

    assert (
        family_status(without_proposal, "structured_plan_proposal")
        is CoverageStatus.PARTIAL
    )
    assert (
        family_status(with_proposal, "structured_plan_proposal")
        is CoverageStatus.COVERED
    )
    assert (
        family_status(without_proposal, "deterministic_safe_fallback")
        is CoverageStatus.COVERED
    )


def test_multi_case_source_group_requires_two_completed_cases() -> None:
    contract = load_development_coverage_contract()
    first = synthetic_contract_case(1, group_index=7)
    second = synthetic_contract_case(2, group_index=7)

    partial = evaluate_development_coverage(
        contract,
        (first, second),
        (completed_result(first),),
    )
    covered = evaluate_development_coverage(
        contract,
        (first, second),
        (completed_result(first), completed_result(second)),
    )

    assert (
        family_status(partial, "multi_case_source_group")
        is CoverageStatus.PARTIAL
    )
    assert (
        family_status(covered, "multi_case_source_group")
        is CoverageStatus.COVERED
    )


def test_public_forum_never_covers_multi_case_source_group() -> None:
    contract = load_development_coverage_contract()
    first = synthetic_public_forum_case(1)
    second = synthetic_public_forum_case(2)

    report = evaluate_development_coverage(
        contract,
        (first, second),
        (completed_result(first), completed_result(second)),
    )

    assert (
        family_status(report, "multi_case_source_group")
        is CoverageStatus.MISSING
    )


def test_existing_split_contract_produces_isolated_sets_accepted_by_checker() -> None:
    contract = load_development_coverage_contract()
    cases = tuple(synthetic_contract_case(index) for index in range(1, 25))
    development, final = split_cases(cases, version="coverage-v0.1-test")

    report = evaluate_development_coverage(
        contract,
        development,
        final_cases=final,
    )

    assert report.version == contract.version


def test_checker_rejects_development_final_source_group_overlap() -> None:
    contract = load_development_coverage_contract()
    development = synthetic_contract_case(1, group_index=9)
    final = synthetic_contract_case(2, group_index=9)

    with pytest.raises(FinalUnseenIsolationError, match="must be disjoint"):
        evaluate_development_coverage(
            contract,
            (development,),
            final_cases=(final,),
        )


def test_checker_rejects_public_forum_in_final_unseen() -> None:
    contract = load_development_coverage_contract()
    public_case = synthetic_public_forum_case(1)

    with pytest.raises(
        FinalUnseenIsolationError,
        match="cannot enter final unseen",
    ):
        evaluate_development_coverage(
            contract,
            (),
            final_cases=(public_case,),
        )


def test_versioned_artifact_contains_only_controlled_taxonomy() -> None:
    raw = DEFAULT_COVERAGE_CONTRACT_PATH.read_text(encoding="utf-8")
    payload = json.loads(raw)
    forbidden_fields = {
        "case_id",
        "facts",
        "response_text",
        "source_group_id",
        "user_message",
    }

    def field_names(value: object) -> set[str]:
        if isinstance(value, dict):
            return set(value) | {
                name for item in value.values() for name in field_names(item)
            }
        if isinstance(value, list):
            return {name for item in value for name in field_names(item)}
        return set()

    assert forbidden_fields.isdisjoint(field_names(payload))
    assert '"RL' not in raw
    assert '"RG' not in raw


def test_private_raw_fixture_is_not_copied_to_repository_artifact(
    tmp_path: Path,
) -> None:
    private_marker = "PRIVATE-INTAKE-CONTENT-MUST-STAY-LOCAL"
    private_input = tmp_path / "private" / "input.jsonl"
    private_input.parent.mkdir()
    private_input.write_text(private_marker, encoding="utf-8")

    repository_artifact = DEFAULT_COVERAGE_CONTRACT_PATH.read_text(
        encoding="utf-8"
    )

    assert private_marker in private_input.read_text(encoding="utf-8")
    assert private_marker not in repository_artifact


def test_private_content_never_enters_aggregate_coverage_report() -> None:
    contract = load_development_coverage_contract()
    raw_message = "PRIVATE-RAW-LEARNER-CONTENT"
    raw_response = "PRIVATE-MODEL-RESPONSE"
    case = synthetic_contract_case(1, message=raw_message)

    report = evaluate_development_coverage(
        contract,
        (case,),
        (completed_result(case, response_text=raw_response),),
    )
    serialized = report.model_dump_json()

    assert raw_message not in serialized
    assert raw_response not in serialized
    assert case.case_id not in serialized
    assert case.source_group_id not in serialized


def test_public_provenance_never_enters_aggregate_coverage_report() -> None:
    contract = load_development_coverage_contract()
    case = synthetic_public_forum_case(1)
    assert case.public_provenance is not None
    source_url = str(case.public_provenance.original_public_url)

    report = evaluate_development_coverage(
        contract,
        (case,),
        (completed_result(case),),
    )
    serialized = report.model_dump_json()

    assert source_url not in serialized
    assert case.public_provenance.platform_domain not in serialized
