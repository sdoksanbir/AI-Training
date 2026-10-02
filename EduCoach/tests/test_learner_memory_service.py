from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from educoach.models import (
    ContextType,
    Learner,
    LearningContext,
)
from educoach.persistence import (
    create_schema,
    create_session_factory,
    create_sqlite_engine,
)
from educoach.persistence.tables import LearnerRow
from educoach.repositories import LearnerRepository
from educoach.services import LearnerMemoryService


@pytest.fixture
def session_factory_fixture() -> sessionmaker[Session]:
    engine = create_sqlite_engine(
        "sqlite+pysqlite:///:memory:"
    )
    create_schema(engine)

    factory = create_session_factory(engine)

    yield factory

    engine.dispose()


def test_register_learner_with_multiple_contexts_commits_together(
    session_factory_fixture: sessionmaker[Session],
) -> None:
    learner = Learner(display_name="Ada")

    school_context = LearningContext(
        learner_id=learner.learner_id,
        context_type=ContextType.SCHOOL,
        program_code="school_11",
        grade_level=11,
    )

    exam_context = LearningContext(
        learner_id=learner.learner_id,
        context_type=ContextType.ENTRANCE_EXAM,
        program_code="yks",
    )

    service = LearnerMemoryService(
        session_factory_fixture
    )

    service.register_learner(
        learner,
        [school_context, exam_context],
    )

    with session_factory_fixture() as session:
        repository = LearnerRepository(session)

        loaded = repository.get_learner(
            learner.learner_id
        )

        contexts = repository.list_contexts(
            learner.learner_id
        )

    assert loaded is not None
    assert loaded.display_name == "Ada"

    assert {
        context.program_code
        for context in contexts
    } == {"school_11", "yks"}


def test_register_learner_without_context_is_allowed(
    session_factory_fixture: sessionmaker[Session],
) -> None:
    learner = Learner()

    LearnerMemoryService(
        session_factory_fixture
    ).register_learner(learner)

    with session_factory_fixture() as session:
        loaded = LearnerRepository(
            session
        ).get_learner(
            learner.learner_id
        )

    assert loaded is not None


def test_register_learner_rejects_context_owned_by_another_learner(
    session_factory_fixture: sessionmaker[Session],
) -> None:
    learner = Learner()

    foreign_context = LearningContext(
        learner_id=uuid4(),
        context_type=ContextType.SCHOOL,
        program_code="school_8",
        grade_level=8,
    )

    service = LearnerMemoryService(
        session_factory_fixture
    )

    with pytest.raises(ValueError):
        service.register_learner(
            learner,
            [foreign_context],
        )

    with session_factory_fixture() as session:
        loaded = LearnerRepository(
            session
        ).get_learner(
            learner.learner_id
        )

    assert loaded is None


def test_register_learner_rolls_back_entire_transaction_on_failure(
    session_factory_fixture: sessionmaker[Session],
) -> None:
    learner = Learner()
    duplicated_context_id = uuid4()

    first_context = LearningContext(
        context_id=duplicated_context_id,
        learner_id=learner.learner_id,
        context_type=ContextType.SCHOOL,
        program_code="school_11",
        grade_level=11,
    )

    second_context = LearningContext(
        context_id=duplicated_context_id,
        learner_id=learner.learner_id,
        context_type=ContextType.ENTRANCE_EXAM,
        program_code="yks",
    )

    service = LearnerMemoryService(
        session_factory_fixture
    )

    with pytest.raises(IntegrityError):
        service.register_learner(
            learner,
            [first_context, second_context],
        )

    with session_factory_fixture() as session:
        repository = LearnerRepository(session)

        loaded = repository.get_learner(
            learner.learner_id
        )

        contexts = repository.list_contexts(
            learner.learner_id
        )

    assert loaded is None
    assert contexts == []


def test_service_remains_usable_after_transaction_failure(
    session_factory_fixture: sessionmaker[Session],
) -> None:
    failed_learner = Learner()
    duplicated_context_id = uuid4()

    contexts = [
        LearningContext(
            context_id=duplicated_context_id,
            learner_id=failed_learner.learner_id,
            context_type=ContextType.SCHOOL,
            program_code="school_11",
            grade_level=11,
        ),
        LearningContext(
            context_id=duplicated_context_id,
            learner_id=failed_learner.learner_id,
            context_type=ContextType.ENTRANCE_EXAM,
            program_code="yks",
        ),
    ]

    service = LearnerMemoryService(
        session_factory_fixture
    )

    with pytest.raises(IntegrityError):
        service.register_learner(
            failed_learner,
            contexts,
        )

    valid_learner = Learner(
        display_name="Rollback sonrası"
    )

    service.register_learner(valid_learner)

    with session_factory_fixture() as session:
        loaded = LearnerRepository(
            session
        ).get_learner(
            valid_learner.learner_id
        )

    assert loaded is not None
    assert loaded.display_name == "Rollback sonrası"


def test_service_does_not_commit_unrelated_caller_session(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "transaction-isolation.db"

    engine = create_sqlite_engine(
        f"sqlite+pysqlite:///{database_path.as_posix()}"
    )
    create_schema(engine)

    factory = create_session_factory(engine)

    pending_learner = Learner(
        display_name="Henüz commit edilmedi"
    )

    caller_session = factory()

    try:
        caller_session.add(
            LearnerRow(
                learner_id=str(
                    pending_learner.learner_id
                ),
                display_name=pending_learner.display_name,
                education_status=(
                    pending_learner.education_status.value
                ),
                preferred_language=(
                    pending_learner.preferred_language
                ),
                timezone=pending_learner.timezone,
                created_at=pending_learner.created_at,
                updated_at=pending_learner.updated_at,
            )
        )

        committed_learner = Learner(
            display_name="Servis tarafından kaydedildi"
        )

        LearnerMemoryService(
            factory
        ).register_learner(
            committed_learner
        )

        with factory() as verifier:
            repository = LearnerRepository(verifier)

            committed = repository.get_learner(
                committed_learner.learner_id
            )

            unrelated = repository.get_learner(
                pending_learner.learner_id
            )

        assert committed is not None
        assert unrelated is None

    finally:
        caller_session.rollback()
        caller_session.close()
        engine.dispose()
