"""Create deterministic source-group-safe development/final splits."""

import argparse
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evaluations.real_learner import (  # noqa: E402
    CaseFileValidationError,
    load_validated_cases,
    write_split,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Split validated learner cases by stable source group."
    )
    parser.add_argument("input", type=Path)
    parser.add_argument("--version", required=True)
    parser.add_argument("--development-output", required=True, type=Path)
    parser.add_argument("--final-output", required=True, type=Path)
    parser.add_argument("--manifest-output", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        cases = load_validated_cases(args.input)
        manifest = write_split(
            cases,
            version=args.version,
            development_path=args.development_output,
            final_path=args.final_output,
            manifest_path=args.manifest_output,
        )
    except CaseFileValidationError as error:
        print("Validation failed.", file=sys.stderr)
        for detail in error.errors:
            print(f"- {detail}", file=sys.stderr)
        return 1
    except (FileExistsError, OSError, ValueError) as error:
        print(f"Split failed: {error}", file=sys.stderr)
        return 1
    print(
        "Split complete: "
        f"{manifest.development_case_count} development, "
        f"{manifest.final_case_count} final unseen."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
