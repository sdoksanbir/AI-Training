from sqlalchemy.orm import Session, sessionmaker

from educoach.llm import FakeLLMProvider
from educoach.models import ContextType, Learner, LearningContext
from educoach.orchestrator import CoachOrchestrator
from educoach.persistence import create_schema, create_session_factory, create_sqlite_engine
from educoach.services import LearnerMemoryService
import pytest


def test_orchestrator_builds_memory_context_and_validates_response() -> None:
    engine = create_sqlite_engine("sqlite+pysqlite:///:memory:")
    create_schema(engine)
    factory: sessionmaker[Session] = create_session_factory(engine)
    learner = Learner(display_name="Ali")
    context = LearningContext(
        learner_id=learner.learner_id,
        context_type=ContextType.ENTRANCE_EXAM,
        program_code="yks",
    )
    LearnerMemoryService(factory).register_learner(learner, [context])
    provider = FakeLLMProvider(responder=lambda request: "Önce mevcut durumunu birlikte inceleyelim.")

    result = CoachOrchestrator(
        LearnerMemoryService(factory), provider
    ).respond(learner.learner_id, "Bugün ne çalışmalıyım?")

    assert result.text.startswith("Önce")
    assert provider.requests[0].user_message == "Bugün ne çalışmalıyım?"
    assert "Ali" in provider.requests[0].memory_context
    engine.dispose()


def test_orchestrator_rejects_empty_user_message() -> None:
    provider = FakeLLMProvider()
    with pytest.raises(ValueError, match="cannot be empty"):
        # Input validation must happen before memory or provider access.
        CoachOrchestrator(None, provider).respond(__import__("uuid").uuid4(), "   ")


def test_orchestrator_rejects_empty_model_response() -> None:
    engine = create_sqlite_engine("sqlite+pysqlite:///:memory:")
    create_schema(engine)
    factory = create_session_factory(engine)
    learner = Learner()
    context = LearningContext(
        learner_id=learner.learner_id,
        context_type=ContextType.SCHOOL,
        program_code="school_11",
    )
    LearnerMemoryService(factory).register_learner(learner, [context])
    with pytest.raises(ValueError, match="empty_response"):
        CoachOrchestrator(
            LearnerMemoryService(factory), FakeLLMProvider(responder=lambda _: "")
        ).respond(learner.learner_id, "yardım et")
    engine.dispose()
