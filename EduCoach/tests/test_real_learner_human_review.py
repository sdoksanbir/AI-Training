"""Synthetic fixtures for aggregate-only manual review tooling."""

import json
from pathlib import Path

from evaluations.real_learner import (
    DevelopmentCaseResult,
    DevelopmentRunSummary,
    ExecutionStatus,
    HumanReviewRecord,
    RealLearnerEvaluationCase,
    RuntimeMetadata,
    load_development_coverage_contract,
    summarize_human_reviews,
)
import scripts.summarize_real_learner_human_review as review_cli


def synthetic_case(
    index: int,
    *,
    program_code: str = "yks",
    expected_tags: tuple[str, ...] = ("recommend_exam_analysis",),
    forbidden_tags: tuple[str, ...] = ("recommend_more_hours_by_default",),
    raw_message: str = "Synthetic review fixture; not learner evidence.",
) -> RealLearnerEvaluationCase:
    return RealLearnerEvaluationCase.model_validate(
        {
            "case_id": f"RL{index:04d}",
            "source_group_id": f"RG{index:04d}",
            "source_kind": "real_anonymized",
            "category": "review_fixture",
            "program_code": program_code,
            "user_message": raw_message,
            "facts": [],
            "expected_behavior_tags": list(expected_tags),
            "forbidden_behavior_tags": list(forbidden_tags),
            "privacy_reviewed": True,
            "usage_authorized": True,
        }
    )


def completed_result(
    case: RealLearnerEvaluationCase,
    *,
    model: str = "qwen3:14b",
    response_text: str = "Synthetic private response.",
    proposal_present: bool = False,
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


def review_record(
    case: RealLearnerEvaluationCase,
    *,
    response_text: str = "Synthetic private response.",
    expected_review: str | None = None,
    forbidden_review: str | None = None,
    notes: str | None = None,
) -> HumanReviewRecord:
    return HumanReviewRecord.model_validate(
        {
            "case_id": case.case_id,
            "expected_behavior_tags": list(case.expected_behavior_tags),
            "forbidden_behavior_tags": list(case.forbidden_behavior_tags),
            "response_text": response_text,
            "proposal_review": None,
            "expected_review": expected_review,
            "forbidden_review": forbidden_review,
            "notes": notes,
        }
    )


def write_jsonl(path: Path, models: tuple[object, ...]) -> None:
    path.write_text(
        "".join(
            json.dumps(model.model_dump(mode="json"), ensure_ascii=False) + "\n"
            for model in models
        ),
        encoding="utf-8",
    )


def test_unreviewed_completed_case_is_not_counted_as_reviewed() -> None:
    case = synthetic_case(1)
    summary = summarize_human_reviews(
        load_development_coverage_contract(),
        (case,),
        (completed_result(case),),
        (review_record(case),),
        run_id="dev-review-test",
    )

    assert summary.completed_count == 1
    assert summary.reviewed_count == 0
    assert summary.incomplete_review_count == 1
    assert summary.expected_review.unreviewed == 1
    assert summary.forbidden_review.unreviewed == 1


def test_manual_decisions_keep_present_and_unclear_separate() -> None:
    present = synthetic_case(1)
    unclear = synthetic_case(2)
    summary = summarize_human_reviews(
        load_development_coverage_contract(),
        (present, unclear),
        (completed_result(present), completed_result(unclear)),
        (
            review_record(
                present,
                expected_review="not_met",
                forbidden_review="present",
                notes="Human reviewer found a prohibited behavior.",
            ),
            review_record(
                unclear,
                expected_review="unclear",
                forbidden_review="unclear",
                notes="Human reviewer found insufficient evidence.",
            ),
        ),
        run_id="dev-review-test",
    )

    assert summary.expected_review.not_met == 1
    assert summary.expected_review.unclear == 1
    assert summary.forbidden_review.present == 1
    assert summary.forbidden_review.unclear == 1
    assert summary.reviewed_count == 2


def test_fallback_quality_terminology_is_aggregated_without_judging() -> None:
    acceptable = synthetic_case(1)
    low_utility = synthetic_case(2)
    unreviewed = synthetic_case(3)
    cases = (acceptable, low_utility, unreviewed)
    results = tuple(
        completed_result(case, model="deterministic") for case in cases
    )
    reviews = (
        review_record(
            acceptable,
            expected_review="met",
            forbidden_review="absent",
            notes="SAFE_FALLBACK_ACCEPTABLE",
        ),
        review_record(
            low_utility,
            expected_review="not_met",
            forbidden_review="absent",
            notes="SAFE_FALLBACK_LOW_UTILITY",
        ),
        review_record(unreviewed),
    )

    summary = summarize_human_reviews(
        load_development_coverage_contract(),
        cases,
        results,
        reviews,
        run_id="dev-review-test",
    )

    assert summary.fallback.fallback_count == 3
    assert summary.fallback.acceptable == 1
    assert summary.fallback.low_utility == 1
    assert summary.fallback.unreviewed_or_invalid == 1
    assert summary.fallback_rate == 1.0


def test_summary_contains_no_raw_learner_or_response_content() -> None:
    raw_message = "PRIVATE-RAW-LEARNER-MARKER"
    raw_response = "PRIVATE-RAW-RESPONSE-MARKER"
    case = synthetic_case(1, raw_message=raw_message)
    summary = summarize_human_reviews(
        load_development_coverage_contract(),
        (case,),
        (completed_result(case, response_text=raw_response),),
        (review_record(case, response_text=raw_response),),
        run_id="dev-review-test",
    )
    serialized = summary.model_dump_json()

    assert raw_message not in serialized
    assert raw_response not in serialized
    assert case.case_id not in serialized
    assert case.source_group_id not in serialized


def test_family_and_program_review_counts_use_completed_cases_only() -> None:
    yks = synthetic_case(1)
    school = synthetic_case(
        2,
        program_code="school_7",
        expected_tags=("address_parent_not_learner",),
        forbidden_tags=("punitive_study_advice",),
    )
    summary = summarize_human_reviews(
        load_development_coverage_contract(),
        (yks, school),
        (completed_result(yks), completed_result(school)),
        (
            review_record(
                yks,
                expected_review="met",
                forbidden_review="absent",
                notes="Human-reviewed useful response.",
            ),
            review_record(school),
        ),
        run_id="dev-review-test",
    )
    keyed = {
        (item.family_id, item.program_code): item
        for item in summary.family_program
    }

    assert keyed[("exam_analysis", "yks")].completed_count == 1
    assert keyed[("exam_analysis", "yks")].reviewed_count == 1
    assert keyed[("parent_reporter", "school_7")].completed_count == 1
    assert keyed[("parent_reporter", "school_7")].unreviewed_count == 1


def test_proposal_presence_is_counted_without_implying_human_approval() -> None:
    case = synthetic_case(1)
    summary = summarize_human_reviews(
        load_development_coverage_contract(),
        (case,),
        (completed_result(case, proposal_present=True),),
        (review_record(case),),
        run_id="dev-review-test",
    )

    assert summary.proposal_count == 1
    assert summary.proposal_review_presence_count == 0
    assert summary.reviewed_count == 0


def test_cli_writes_only_aggregates_and_does_not_read_final_unseen(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    private_root = tmp_path / "private"
    run_directory = private_root / "runs" / "dev-review-test"
    run_directory.mkdir(parents=True)
    raw_message = "PRIVATE-DEVELOPMENT-MESSAGE"
    raw_response = "PRIVATE-DEVELOPMENT-RESPONSE"
    case = synthetic_case(1, raw_message=raw_message)
    result = completed_result(case, response_text=raw_response)
    review = review_record(case, response_text=raw_response)
    development_input = private_root / "development.jsonl"
    write_jsonl(development_input, (case,))
    write_jsonl(run_directory / "results.jsonl", (result,))
    write_jsonl(run_directory / "human_review.jsonl", (review,))
    (run_directory / "summary.json").write_text(
        DevelopmentRunSummary(
            run_id="dev-review-test",
            total_cases=1,
            completed=1,
            not_run=0,
            failed=0,
            proposal_count=0,
            unsupported_fact_kind_count=0,
        ).model_dump_json(),
        encoding="utf-8",
    )
    final_marker = "FINAL-UNSEEN-MUST-NOT-BE-CONSUMED"
    final_path = private_root / "final-unseen.jsonl"
    final_path.write_text(final_marker, encoding="utf-8")
    monkeypatch.setattr(review_cli, "require_private_path", lambda path: path)

    exit_code = review_cli.main(
        [str(development_input), str(run_directory)]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert final_path.read_text(encoding="utf-8") == final_marker
    combined = (
        (run_directory / "coverage.json").read_text(encoding="utf-8")
        + (run_directory / "human_review_summary.json").read_text(
            encoding="utf-8"
        )
        + captured.out
        + captured.err
    )
    assert raw_message not in combined
    assert raw_response not in combined
    assert final_marker not in combined
