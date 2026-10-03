import educoach


def test_educoach_package_is_importable() -> None:
    assert educoach.__version__ == "0.1.0"
from educoach.cli import build_parser


def test_cli_parser_accepts_learner_message() -> None:
    args = build_parser().parse_args([
        "--database", "memory.db",
        "--learner-id", "00000000-0000-0000-0000-000000000001",
        "Bugün ne çalışmalıyım?",
    ])
    assert args.model == "qwen3:14b"
    assert args.message == "Bugün ne çalışmalıyım?"
