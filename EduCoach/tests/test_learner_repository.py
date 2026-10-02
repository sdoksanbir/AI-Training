from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from educoach.models import (
    ContextType,
    EducationStatus,
    Learner,
    LearningContext,
)
from educoach.persistence import (
    create_schema,
    create_session_factory,
    create_sqlite_engine,
)
from educoach.repositories import LearnerRepository


@pytest.fixture
def session() -> Session:
    engine = create_sqlite_engine(
        "sqlite+pysqlite:///:memory:"
    )
    create_schema(engine)

    factory = create_session_factory(engine)

    with factory() as session:
        yield session

    engine.dispose()


def test_sqlite_foreign_keys_are_enabled(
    session: Session,
) -> None:
    enabled = session.execute(
        text("PRAGMA foreign_keys")
    ).scalar_one()

    assert enabled == 1


def test_learner_round_trip(
    session: Session,
) -> None:
    learner = Learner(
        display_name="Ada",
        education_status=EducationStatus.HIGH_SCHOOL,
        preferred_language="tr",
        timezone="Europe/Istanbul",
    )

    repository = LearnerRepository(session)
    repository.add_learner(learner)
    session.commit()

    loaded = repository.get_learner(
        learner.learner_id
    )

    assert loaded is not None
    assert loaded.learner_id == learner.learner_id
    assert loaded.display_name == "Ada"
    assert (
        loaded.education_status
        == EducationStatus.HIGH_SCHOOL
    )
    assert loaded.preferred_language == "tr"
    assert loaded.timezone == "Europe/Istanbul"


def test_learning_context_round_trip(
    session: Session,
) -> None:
    learner = Learner()

    context = LearningContext(
        learner_id=learner.learner_id,
        context_type=ContextType.ENTRANCE_EXAM,
        program_code="yks",
        grade_level=12,
        exam_year=2027,
    )

    repository = LearnerRepository(session)

    repository.add_learner(learner)
    repository.add_context(context)
    session.commit()

    loaded = repository.get_context(
        context.context_id
    )

    assert loaded is not None
    assert loaded.context_id == context.context_id
    assert loaded.learner_id == learner.learner_id
    assert loaded.program_code == "yks"
    assert loaded.grade_level == 12
    assert loaded.exam_year == 2027


def test_same_learner_can_have_multiple_contexts(
    session: Session,
) -> None:
    learner = Learner()

    school_context = LearningContext(
        learner_id=learner.learner_id,
        context_type=ContextType.SCHOOL,
        program_code="school_11",
        grade_level=11,
    )

    yks_context = LearningContext(
        learner_id=learner.learner_id,
        context_type=ContextType.ENTRANCE_EXAM,
        program_code="yks",
    )

    repository = LearnerRepository(session)

    repository.add_learner(learner)
    repository.add_context(school_context)
    repository.add_context(yks_context)
    session.commit()

    contexts = repository.list_contexts(
        learner.learner_id
    )

    assert len(contexts) == 2
    assert {
        context.program_code
        for context in contexts
    } == {"school_11", "yks"}


def test_orphan_learning_context_is_rejected_by_database(
    session: Session,
) -> None:
    context = LearningContext(
        learner_id=uuid4(),
        context_type=ContextType.SCHOOL,
        program_code="school_7",
        grade_level=7,
    )

    repository = LearnerRepository(session)

    with pytest.raises(IntegrityError):
        repository.add_context(context)

    session.rollback()
