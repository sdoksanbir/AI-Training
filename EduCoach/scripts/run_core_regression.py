"""Run deterministic EduCoach core regression checks."""

from dataclasses import dataclass
from datetime import date

from educoach.llm import FakeLLMProvider
from educoach.models import (
    Assessment,
    AssessmentResult,
    ContextType,
    Learner,
    LearningContext,
)
from educoach.orchestrator import (
    CoachOrchestrator,
    ResponseRegenerationExhausted,
)
from educoach.persistence import create_schema, create_session_factory, create_sqlite_engine
from educoach.rag import InMemoryRetriever, KnowledgeChunk
from educoach.services import LearnerMemoryService


@dataclass(frozen=True)
class RegressionResult:
    name: str
    passed: bool


class _RecordingRetriever(InMemoryRetriever):
    def __init__(self, chunks: list[KnowledgeChunk]) -> None:
        super().__init__(chunks)
        self.call_count = 0

    def search(self, query, limit=3, filters=None):
        self.call_count += 1
        return super().search(query, limit=limit, filters=filters)


def _new_memory() -> tuple[object, LearnerMemoryService]:
    engine = create_sqlite_engine("sqlite+pysqlite:///:memory:")
    create_schema(engine)
    factory = create_session_factory(engine)
    return engine, LearnerMemoryService(factory)


def _base_runtime_checks() -> list[RegressionResult]:
    engine, memory = _new_memory()
    learner = Learner(display_name="Regression")
    context = LearningContext(
        learner_id=learner.learner_id,
        context_type=ContextType.ENTRANCE_EXAM,
        program_code="yks",
    )
    memory.register_learner(learner, [context])
    provider = FakeLLMProvider(responder=lambda _: "Planını birlikte inceleyelim.")
    retriever = InMemoryRetriever([
        KnowledgeChunk("yks-1", "YKS çalışma planı", "YKS", "regression", {"program": "yks"}),
        KnowledgeChunk("lgs-1", "LGS çalışma planı", "LGS", "regression", {"program": "lgs"}),
    ])
    response = CoachOrchestrator(memory, provider, retriever).respond(
        learner.learner_id, "YKS çalışma planı"
    )
    context_text = provider.requests[-1].memory_context
    results = [
        RegressionResult(
            "response_generated",
            bool(response.text) and len(provider.requests) == 1,
        ),
        RegressionResult("learner_context_present", "Regression" in context_text),
        RegressionResult("program_filter_applied", "YKS" in context_text and "LGS" not in context_text),
    ]
    engine.dispose()
    return results


def _repetition_loop_auto_fixed() -> RegressionResult:
    engine, memory = _new_memory()
    learner = Learner(display_name="Repetition Regression")
    context = LearningContext(
        learner_id=learner.learner_id,
        context_type=ContextType.SCHOOL,
        program_code="school_11",
        grade_level=11,
    )
    memory.register_learner(learner, [context])
    repeated = (
        "Matematik yanlışlarını dikkatle analiz et.\n"
        "Matematik yanlışlarını dikkatle analiz et.\n"
        "Matematik yanlışlarını dikkatle analiz et.\n"
        "Sonra soru çöz."
    )
    provider = FakeLLMProvider(responder=lambda _: repeated)
    response = CoachOrchestrator(memory, provider).respond(
        learner.learner_id,
        "Bugünkü çalışmamı değerlendir",
    )
    passed = (
        response.text
        == "Matematik yanlışlarını dikkatle analiz et.\nSonra soru çöz."
        and len(provider.requests) == 1
    )
    engine.dispose()
    return RegressionResult("repetition_loop_auto_fixed", passed)


def _numeric_claim_regenerated() -> RegressionResult:
    engine, memory = _new_memory()
    learner = Learner(display_name="Numeric Regression")
    context = LearningContext(
        learner_id=learner.learner_id,
        context_type=ContextType.ENTRANCE_EXAM,
        program_code="yks",
        grade_level=12,
    )
    memory.register_learner(learner, [context])
    assessment = Assessment(
        learner_id=learner.learner_id,
        context_id=context.context_id,
        assessment_type="mock_exam",
        assessment_name="TYT denemesi",
        assessment_date=date(2026, 10, 5),
    )
    memory.record_assessment(
        assessment,
        results=[
            AssessmentResult(
                assessment_id=assessment.assessment_id,
                area_type="section",
                area_code="tyt",
                net=74,
            )
        ],
    )
    responses = iter([
        "TYT puanın 74 olduğu için bu konuya odaklanmalısın.",
        "Son TYT denemende 74 net yaptın.",
    ])
    provider = FakeLLMProvider(responder=lambda _: next(responses))
    response = CoachOrchestrator(memory, provider).respond(
        learner.learner_id,
        "Son deneme sonucumu değerlendir",
    )
    passed = (
        response.text == "Son TYT denemende 74 net yaptın."
        and len(provider.requests) == 2
    )
    engine.dispose()
    return RegressionResult("numeric_claim_regenerated", passed)


def _regeneration_budget_bounded() -> RegressionResult:
    engine, memory = _new_memory()
    learner = Learner(display_name="Budget Regression")
    context = LearningContext(
        learner_id=learner.learner_id,
        context_type=ContextType.SCHOOL,
        program_code="school_11",
        grade_level=11,
    )
    memory.register_learner(learner, [context])
    provider = FakeLLMProvider(responder=lambda _: "Sen 10. sınıftasın.")
    exhausted = False
    try:
        CoachOrchestrator(memory, provider).respond(
            learner.learner_id,
            "Sınıf düzeyimi değerlendir",
        )
    except ResponseRegenerationExhausted:
        exhausted = True
    passed = exhausted and len(provider.requests) == 2
    engine.dispose()
    return RegressionResult("regeneration_budget_bounded", passed)


def _ambiguous_context_stops_generation() -> RegressionResult:
    engine, memory = _new_memory()
    learner = Learner(display_name="Ambiguous Regression")
    contexts = [
        LearningContext(
            learner_id=learner.learner_id,
            context_type=ContextType.SCHOOL,
            program_code="school_11",
            grade_level=11,
        ),
        LearningContext(
            learner_id=learner.learner_id,
            context_type=ContextType.ENTRANCE_EXAM,
            program_code="yks",
        ),
    ]
    memory.register_learner(learner, contexts)
    provider = FakeLLMProvider()
    retriever = _RecordingRetriever([])
    response = CoachOrchestrator(memory, provider, retriever).respond(
        learner.learner_id,
        "Genel bir çalışma isteğim var",
    )
    passed = (
        response.model == "deterministic"
        and not provider.requests
        and retriever.call_count == 0
    )
    engine.dispose()
    return RegressionResult("ambiguous_context_stops_generation", passed)


def _learner_memory_isolated() -> RegressionResult:
    engine, memory = _new_memory()
    learner_a = Learner(display_name="Learner Alpha")
    context_a = LearningContext(
        learner_id=learner_a.learner_id,
        context_type=ContextType.SCHOOL,
        program_code="alpha_school_11",
        grade_level=11,
    )
    learner_b = Learner(display_name="UNIQUE_BETA_SECRET")
    context_b = LearningContext(
        learner_id=learner_b.learner_id,
        context_type=ContextType.SCHOOL,
        program_code="unique_beta_program",
        grade_level=12,
    )
    memory.register_learner(learner_a, [context_a])
    memory.register_learner(learner_b, [context_b])
    provider = FakeLLMProvider(responder=lambda _: "Hazırım.")
    CoachOrchestrator(memory, provider).respond(
        learner_a.learner_id,
        "Hafızamı kullan",
    )
    memory_context = provider.requests[-1].memory_context
    passed = (
        "Learner Alpha" in memory_context
        and "UNIQUE_BETA_SECRET" not in memory_context
        and "unique_beta_program" not in memory_context
        and str(context_b.context_id) not in memory_context
    )
    engine.dispose()
    return RegressionResult("learner_memory_isolated", passed)


def run() -> list[RegressionResult]:
    return [
        *_base_runtime_checks(),
        _repetition_loop_auto_fixed(),
        _numeric_claim_regenerated(),
        _regeneration_budget_bounded(),
        _ambiguous_context_stops_generation(),
        _learner_memory_isolated(),
    ]


if __name__ == "__main__":
    results = run()
    for result in results:
        print(f"{'PASS' if result.passed else 'FAIL'} {result.name}")
    raise SystemExit(0 if all(result.passed for result in results) else 1)
