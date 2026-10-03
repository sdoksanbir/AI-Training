import educoach


def test_educoach_package_is_importable() -> None:
    assert educoach.__version__ == "0.1.0"
from educoach.cli import build_parser
from educoach import cli


def test_cli_parser_accepts_learner_message() -> None:
    args = build_parser().parse_args([
        "--database", "memory.db",
        "--learner-id", "00000000-0000-0000-0000-000000000001",
        "Bugün ne çalışmalıyım?",
    ])
    assert args.model == "qwen3:14b"
    assert args.message == "Bugün ne çalışmalıyım?"


def test_cli_stops_when_ollama_is_unhealthy(monkeypatch, capsys) -> None:
    class UnhealthyProvider:
        def __init__(self, model): pass
        def health(self): return False

    monkeypatch.setattr(cli, "OllamaProvider", UnhealthyProvider)
    try:
        cli.main([
            "--database", "memory.db",
            "--learner-id", "00000000-0000-0000-0000-000000000001",
            "Merhaba",
        ])
    except SystemExit as error:
        assert "Ollama erişilemiyor" in str(error)
    else:
        raise AssertionError("CLI unhealthy provider ile devam etti")
