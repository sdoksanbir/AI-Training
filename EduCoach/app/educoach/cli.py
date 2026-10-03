import argparse
from uuid import UUID

from educoach.llm import OllamaProvider
from educoach.orchestrator import CoachOrchestrator
from educoach.persistence import create_session_factory, create_sqlite_engine
from educoach.services import LearnerMemoryService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="EduCoach terminal coach")
    parser.add_argument("--database", required=True, help="SQLite database URL or path")
    parser.add_argument("--learner-id", required=True, type=UUID)
    parser.add_argument("message")
    parser.add_argument("--model", default="qwen3:14b")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    database_url = args.database if "://" in args.database else f"sqlite+pysqlite:///{args.database}"
    engine = create_sqlite_engine(database_url)
    factory = create_session_factory(engine)
    result = CoachOrchestrator(
        LearnerMemoryService(factory), OllamaProvider(args.model)
    ).respond(args.learner_id, args.message)
    print(result.text)
    engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
