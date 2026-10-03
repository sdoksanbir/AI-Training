"""Run deterministic EduCoach core regression checks."""

from dataclasses import dataclass
from uuid import uuid4

from educoach.llm import FakeLLMProvider
from educoach.models import ContextType, Learner, LearningContext
from educoach.orchestrator import CoachOrchestrator
from educoach.persistence import create_schema, create_session_factory, create_sqlite_engine
from educoach.rag import InMemoryRetriever, KnowledgeChunk
from educoach.services import LearnerMemoryService


@dataclass(frozen=True)
class RegressionResult:
    name: str
    passed: bool


def run() -> list[RegressionResult]:
    engine = create_sqlite_engine("sqlite+pysqlite:///:memory:")
    create_schema(engine)
    factory = create_session_factory(engine)
    learner = Learner(display_name="Regression")
    context = LearningContext(
        learner_id=learner.learner_id,
        context_type=ContextType.ENTRANCE_EXAM,
        program_code="yks",
    )
    memory = LearnerMemoryService(factory)
    memory.register_learner(learner, [context])
    provider = FakeLLMProvider(responder=lambda _: "Planını birlikte inceleyelim.")
    retriever = InMemoryRetriever([
        KnowledgeChunk("yks-1", "YKS çalışma planı", "YKS", "regression", {"program": "yks"}),
        KnowledgeChunk("lgs-1", "LGS çalışma planı", "LGS", "regression", {"program": "lgs"}),
    ])
    CoachOrchestrator(memory, provider, retriever).respond(
        learner.learner_id, "Bugün nasıl çalışmalıyım?"
    )
    context_text = provider.requests[-1].memory_context
    results = [
        RegressionResult("response_generated", bool(provider.requests)),
        RegressionResult("learner_context_present", "Regression" in context_text),
        RegressionResult("program_filter_applied", "YKS" in context_text and "LGS" not in context_text),
    ]
    engine.dispose()
    return results


if __name__ == "__main__":
    results = run()
    for result in results:
        print(f"{'PASS' if result.passed else 'FAIL'} {result.name}")
    raise SystemExit(0 if all(result.passed for result in results) else 1)
