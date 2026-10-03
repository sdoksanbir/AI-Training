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


def test_cli_hides_provider_error(monkeypatch) -> None:
    class FailingProvider:
        def __init__(self, model): pass
        def health(self): return True
        def generate(self, request):
            from educoach.llm import OllamaProviderError
            raise OllamaProviderError("secret endpoint details")

    class FailingCoach:
        def __init__(self, memory, provider): pass
        def respond(self, learner_id, message):
            from educoach.llm import OllamaProviderError
            raise OllamaProviderError("secret endpoint details")

    monkeypatch.setattr(cli, "OllamaProvider", FailingProvider)
    monkeypatch.setattr(cli, "CoachOrchestrator", FailingCoach)
    try:
        cli.main([
            "--database", "memory.db",
            "--learner-id", "00000000-0000-0000-0000-000000000001",
            "Merhaba",
        ])
    except SystemExit as error:
        assert "secret endpoint" not in str(error)
        assert "Ollama cevap üretemedi" in str(error)
