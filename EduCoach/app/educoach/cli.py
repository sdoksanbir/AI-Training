import argparse
from uuid import UUID

from educoach.llm import OllamaProvider, OllamaProviderError
from educoach.orchestrator import CoachOrchestrator
from educoach.persistence import create_schema, create_session_factory, create_sqlite_engine
from educoach.services import LearnerMemoryService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="EduCoach terminal coach")
    parser.add_argument("--database", required=True, help="SQLite database URL or path")
    parser.add_argument("--learner-id", required=True, type=UUID)
    parser.add_argument("message")
    parser.add_argument("--model", default="qwen3:14b")
    parser.add_argument("--create-schema", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    database_url = args.database if "://" in args.database else f"sqlite+pysqlite:///{args.database}"
    engine = create_sqlite_engine(database_url)
    if args.create_schema:
        create_schema(engine)
    factory = create_session_factory(engine)
    provider = OllamaProvider(args.model)
    if not provider.health():
        raise SystemExit(
            f"Ollama erişilemiyor veya model yüklü değil: {args.model}"
        )
    try:
        result = CoachOrchestrator(
            LearnerMemoryService(factory), provider
        ).respond(args.learner_id, args.message)
    except ValueError as error:
        raise SystemExit(f"İstek işlenemedi: {error}") from None
    except OllamaProviderError:
        raise SystemExit("Ollama cevap üretemedi; model ve servis durumunu kontrol edin") from None
    print(result.text)
    engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
