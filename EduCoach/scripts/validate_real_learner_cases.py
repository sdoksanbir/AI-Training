"""Validate privacy-reviewed real learner evaluation JSONL."""

import argparse
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evaluations.real_learner import (  # noqa: E402
    CaseFileValidationError,
    load_validated_cases,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate anonymized real learner evaluation JSONL."
    )
    parser.add_argument("input", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        cases = load_validated_cases(args.input)
    except CaseFileValidationError as error:
        print("Validation failed.", file=sys.stderr)
        for detail in error.errors:
            print(f"- {detail}", file=sys.stderr)
        return 1
    print(f"Validated {len(cases)} privacy-reviewed cases.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
