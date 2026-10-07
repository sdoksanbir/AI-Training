"""Build content-free coverage and manual-review summaries for one dev run."""

import argparse
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evaluations.real_learner import (  # noqa: E402
    CoverageContractError,
    ReviewArtifactError,
    evaluate_development_coverage,
    load_development_coverage_contract,
    load_development_results,
    load_development_run_summary,
    load_human_reviews,
    load_validated_cases,
    require_private_path,
    summarize_human_reviews,
    write_private_aggregate,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Summarize an existing private development run."
    )
    parser.add_argument("development_input", type=Path)
    parser.add_argument("run_directory", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        development_input = require_private_path(args.development_input)
        run_directory = require_private_path(args.run_directory)
        cases = load_validated_cases(development_input)
        results = load_development_results(run_directory / "results.jsonl")
        reviews = load_human_reviews(run_directory / "human_review.jsonl")
        run_summary = load_development_run_summary(run_directory / "summary.json")
        contract = load_development_coverage_contract()
        coverage = evaluate_development_coverage(contract, cases, results)
        review_summary = summarize_human_reviews(
            contract,
            cases,
            results,
            reviews,
            run_id=run_summary.run_id,
        )
        write_private_aggregate(run_directory / "coverage.json", coverage)
        write_private_aggregate(
            run_directory / "human_review_summary.json",
            review_summary,
        )
    except (CoverageContractError, ReviewArtifactError, ValueError):
        print("Review summary failed: private artifacts are invalid.", file=sys.stderr)
        return 1
    except Exception:
        print("Review summary failed unexpectedly.", file=sys.stderr)
        return 1

    print(
        "Review summary: "
        f"completed={review_summary.completed_count} "
        f"reviewed={review_summary.reviewed_count} "
        f"incomplete={review_summary.incomplete_review_count} "
        f"fallbacks={review_summary.fallback.fallback_count} "
        f"proposals={review_summary.proposal_count}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
