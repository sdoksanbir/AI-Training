"""Run private real-learner development cases through EduCoach runtime."""

import argparse
import os
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from educoach.llm import OllamaProvider  # noqa: E402
from evaluations.real_learner import (  # noqa: E402
    CaseFileValidationError,
    DuplicateCaseError,
    PrivatePathError,
    ProviderUnavailableError,
    load_validated_cases,
    require_private_path,
    run_development_evaluation,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run private development evaluation cases."
    )
    parser.add_argument("input", type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument(
        "--model",
        default=os.environ.get("EDUCOACH_OLLAMA_MODEL"),
        help="Ollama model name; defaults to EDUCOACH_OLLAMA_MODEL.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.model:
        print(
            "Evaluation failed: provider model configuration is required.",
            file=sys.stderr,
        )
        return 2

    try:
        input_path = require_private_path(args.input)
        cases = load_validated_cases(input_path)
        run = run_development_evaluation(
            cases,
            OllamaProvider(args.model),
            run_id=args.run_id,
        )
    except CaseFileValidationError as error:
        print("Evaluation failed: case validation failed.", file=sys.stderr)
        for detail in error.errors:
            print(f"- {detail}", file=sys.stderr)
        return 1
    except (
        DuplicateCaseError,
        FileExistsError,
        PrivatePathError,
        ProviderUnavailableError,
        ValueError,
    ) as error:
        print(f"Evaluation failed: {error}", file=sys.stderr)
        return 1
    except Exception:
        print("Evaluation failed unexpectedly.", file=sys.stderr)
        return 1

    for result in run.results:
        print(f"{result.case_id}: {result.execution_status.value}")
    summary = run.summary
    print(
        "Summary: "
        f"total={summary.total_cases} completed={summary.completed} "
        f"not_run={summary.not_run} failed={summary.failed} "
        f"proposals={summary.proposal_count}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
