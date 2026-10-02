from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from educoach.models import (
    CoachingState,
    CoachingStatus,
    ContextType,
    EvidenceSource,
    Learner,
    LearningContext,
    Preference,
)
from educoach.persistence import (
    create_schema,
    create_session_factory,
    create_sqlite_engine,
)
from educoach.repositories import (
    CoachingStateRepository,
    LearnerRepository,
    PreferenceRepository,
)


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


def make_context(
    session: Session,
) -> tuple[Learner, LearningContext]:
    learner = Learner()

    context = LearningContext(
        learner_id=learner.learner_id,
        context_type=ContextType.LANGUAGE_LEARNING,
        program_code="general_english",
    )

    repository = LearnerRepository(session)
    repository.add_learner(learner)
    repository.add_context(context)

    return learner, context


def test_global_preference_round_trip(
    session: Session,
) -> None:
    learner = Learner()
    LearnerRepository(session).add_learner(learner)

    preference = Preference(
        learner_id=learner.learner_id,
        preference_key="explanation_style",
        preference_value="short",
        source_type=EvidenceSource.LEARNER_REPORTED,
    )

    repository = PreferenceRepository(session)
    repository.add(preference)
    session.commit()

    loaded = repository.get(
        preference.preference_id
    )

    assert loaded is not None
    assert loaded.context_id is None
    assert loaded.preference_value == "short"


def test_preference_value_types_survive_round_trip(
    session: Session,
) -> None:
    learner = Learner()
    LearnerRepository(session).add_learner(learner)

    repository = PreferenceRepository(session)

    values = [
        ("text_value", "evening"),
        ("int_value", 40),
        ("float_value", 0.75),
        ("bool_value", True),
    ]

    preferences = []

    for key, value in values:
        preference = Preference(
            learner_id=learner.learner_id,
            preference_key=key,
            preference_value=value,
        )
        repository.add(preference)
        preferences.append(preference)

    session.commit()

    loaded_values = [
        repository.get(item.preference_id).preference_value
        for item in preferences
    ]

    assert loaded_values == [
        "evening",
        40,
        0.75,
        True,
    ]

    assert type(loaded_values[0]) is str
    assert type(loaded_values[1]) is int
    assert type(loaded_values[2]) is float
    assert type(loaded_values[3]) is bool


def test_context_preference_round_trip(
    session: Session,
) -> None:
    learner, context = make_context(session)

    preference = Preference(
        learner_id=learner.learner_id,
        context_id=context.context_id,
        preference_key="session_minutes",
        preference_value=40,
        source_type=EvidenceSource.PARENT_REPORTED,
        confidence=0.9,
    )

    repository = PreferenceRepository(session)
    repository.add(preference)
    session.commit()

    loaded = repository.get(
        preference.preference_id
    )

    assert loaded is not None
    assert loaded.context_id == context.context_id
    assert loaded.preference_value == 40
    assert loaded.confidence == 0.9
    assert (
        loaded.source_type
        == EvidenceSource.PARENT_REPORTED
    )


def test_preference_cannot_use_another_learners_context(
    session: Session,
) -> None:
    first = Learner()
    second = Learner()

    context = LearningContext(
        learner_id=second.learner_id,
        context_type=ContextType.SCHOOL,
        program_code="school_8",
        grade_level=8,
    )

    learners = LearnerRepository(session)
    learners.add_learner(first)
    learners.add_learner(second)
    learners.add_context(context)

    preference = Preference(
        learner_id=first.learner_id,
        context_id=context.context_id,
        preference_key="study_time",
        preference_value="evening",
    )

    with pytest.raises(IntegrityError):
        PreferenceRepository(session).add(
            preference
        )

    session.rollback()


def test_preference_with_unknown_learner_is_rejected(
    session: Session,
) -> None:
    from uuid import uuid4

    preference = Preference(
        learner_id=uuid4(),
        preference_key="study_time",
        preference_value="evening",
    )

    with pytest.raises(IntegrityError):
        PreferenceRepository(session).add(
            preference
        )

    session.rollback()


def test_global_coaching_state_round_trip(
    session: Session,
) -> None:
    learner = Learner()
    LearnerRepository(session).add_learner(learner)

    state = CoachingState(
        learner_id=learner.learner_id,
        status=CoachingStatus.ACTIVE,
        current_focus="Düzenli çalışma alışkanlığı",
        last_interaction_at=datetime(
            2026, 10, 2, 15, 0, tzinfo=timezone.utc
        ),
        next_review_at=datetime(
            2026, 10, 9, 15, 0, tzinfo=timezone.utc
        ),
    )

    repository = CoachingStateRepository(session)
    repository.add(state)
    session.commit()

    loaded = repository.get(state.state_id)

    assert loaded is not None
    assert loaded.context_id is None
    assert loaded.status == CoachingStatus.ACTIVE
    assert (
        loaded.current_focus
        == "Düzenli çalışma alışkanlığı"
    )
    assert loaded.last_interaction_at is not None
    assert loaded.last_interaction_at.tzinfo is not None


def test_context_coaching_state_round_trip(
    session: Session,
) -> None:
    learner, context = make_context(session)

    state = CoachingState(
        learner_id=learner.learner_id,
        context_id=context.context_id,
        status=CoachingStatus.REVIEW_NEEDED,
        current_focus="Reading",
    )

    repository = CoachingStateRepository(session)
    repository.add(state)
    session.commit()

    loaded = repository.get(state.state_id)

    assert loaded is not None
    assert loaded.context_id == context.context_id
    assert (
        loaded.status
        == CoachingStatus.REVIEW_NEEDED
    )


def test_coaching_state_cannot_use_another_learners_context(
    session: Session,
) -> None:
    first = Learner()
    second = Learner()

    context = LearningContext(
        learner_id=second.learner_id,
        context_type=ContextType.SCHOOL,
        program_code="school_8",
        grade_level=8,
    )

    learners = LearnerRepository(session)
    learners.add_learner(first)
    learners.add_learner(second)
    learners.add_context(context)

    state = CoachingState(
        learner_id=first.learner_id,
        context_id=context.context_id,
        status=CoachingStatus.ACTIVE,
    )

    with pytest.raises(IntegrityError):
        CoachingStateRepository(session).add(
            state
        )

    session.rollback()


def test_coaching_state_with_unknown_learner_is_rejected(
    session: Session,
) -> None:
    from uuid import uuid4

    state = CoachingState(
        learner_id=uuid4(),
    )

    with pytest.raises(IntegrityError):
        CoachingStateRepository(session).add(
            state
        )

    session.rollback()


def test_preference_and_coaching_lists_are_learner_scoped(
    session: Session,
) -> None:
    first = Learner()
    second = Learner()

    learners = LearnerRepository(session)
    learners.add_learner(first)
    learners.add_learner(second)

    preference_repository = PreferenceRepository(
        session
    )
    coaching_repository = CoachingStateRepository(
        session
    )

    preference_repository.add(
        Preference(
            learner_id=first.learner_id,
            preference_key="study_time",
            preference_value="evening",
        )
    )

    preference_repository.add(
        Preference(
            learner_id=second.learner_id,
            preference_key="study_time",
            preference_value="morning",
        )
    )

    coaching_repository.add(
        CoachingState(
            learner_id=first.learner_id,
            status=CoachingStatus.ACTIVE,
        )
    )

    coaching_repository.add(
        CoachingState(
            learner_id=second.learner_id,
            status=CoachingStatus.PAUSED,
        )
    )

    session.commit()

    first_preferences = (
        preference_repository.list_for_learner(
            first.learner_id
        )
    )

    first_states = (
        coaching_repository.list_for_learner(
            first.learner_id
        )
    )

    assert len(first_preferences) == 1
    assert (
        first_preferences[0].preference_value
        == "evening"
    )

    assert len(first_states) == 1
    assert (
        first_states[0].status
        == CoachingStatus.ACTIVE
    )
