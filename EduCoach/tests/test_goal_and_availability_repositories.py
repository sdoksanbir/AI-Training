from datetime import date, time
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from educoach.models import (
    Availability,
    AvailabilityType,
    ContextType,
    DayOfWeek,
    EvidenceSource,
    Goal,
    GoalPriority,
    Learner,
    LearningContext,
)
from educoach.persistence import (
    create_schema,
    create_session_factory,
    create_sqlite_engine,
)
from educoach.repositories import (
    AvailabilityRepository,
    GoalRepository,
    LearnerRepository,
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


def test_goal_round_trip_with_context(
    session: Session,
) -> None:
    learner = Learner()

    context = LearningContext(
        learner_id=learner.learner_id,
        context_type=ContextType.ENTRANCE_EXAM,
        program_code="yks",
    )

    learner_repository = LearnerRepository(session)
    learner_repository.add_learner(learner)
    learner_repository.add_context(context)

    goal = Goal(
        learner_id=learner.learner_id,
        context_id=context.context_id,
        goal_type="exam_target",
        description="TYT netini yükselt",
        target_value=80,
        target_unit="net",
        target_date=date(2027, 6, 1),
        priority=GoalPriority.HIGH,
    )

    repository = GoalRepository(session)
    repository.add(goal)
    session.commit()

    loaded = repository.get(goal.goal_id)

    assert loaded is not None
    assert loaded.goal_id == goal.goal_id
    assert loaded.learner_id == learner.learner_id
    assert loaded.context_id == context.context_id
    assert loaded.target_value == 80
    assert loaded.target_unit == "net"
    assert loaded.priority == GoalPriority.HIGH


def test_goal_without_context_round_trip(
    session: Session,
) -> None:
    learner = Learner()

    LearnerRepository(session).add_learner(
        learner
    )

    goal = Goal(
        learner_id=learner.learner_id,
        goal_type="routine",
        description="Düzenli çalışma alışkanlığı oluştur",
    )

    repository = GoalRepository(session)
    repository.add(goal)
    session.commit()

    loaded = repository.get(goal.goal_id)

    assert loaded is not None
    assert loaded.context_id is None


def test_goal_with_unknown_learner_is_rejected(
    session: Session,
) -> None:
    goal = Goal(
        learner_id=uuid4(),
        goal_type="routine",
        description="Düzenli çalış",
    )

    repository = GoalRepository(session)

    with pytest.raises(IntegrityError):
        repository.add(goal)

    session.rollback()


def test_goal_with_unknown_context_is_rejected(
    session: Session,
) -> None:
    learner = Learner()

    LearnerRepository(session).add_learner(
        learner
    )

    goal = Goal(
        learner_id=learner.learner_id,
        context_id=uuid4(),
        goal_type="exam_target",
        description="Hedef",
        target_value=70,
        target_unit="net",
    )

    repository = GoalRepository(session)

    with pytest.raises(IntegrityError):
        repository.add(goal)

    session.rollback()


def test_availability_minutes_round_trip(
    session: Session,
) -> None:
    learner = Learner()

    LearnerRepository(session).add_learner(
        learner
    )

    availability = Availability(
        learner_id=learner.learner_id,
        day_of_week=DayOfWeek.MONDAY,
        availability_type=AvailabilityType.AVAILABLE,
        available_minutes=120,
        source_type=EvidenceSource.LEARNER_REPORTED,
        notes="Okul sonrası",
    )

    repository = AvailabilityRepository(session)
    repository.add(availability)
    session.commit()

    loaded = repository.get(
        availability.availability_id
    )

    assert loaded is not None
    assert loaded.day_of_week == DayOfWeek.MONDAY
    assert loaded.available_minutes == 120
    assert (
        loaded.source_type
        == EvidenceSource.LEARNER_REPORTED
    )
    assert loaded.notes == "Okul sonrası"


def test_availability_time_range_round_trip(
    session: Session,
) -> None:
    learner = Learner()

    LearnerRepository(session).add_learner(
        learner
    )

    availability = Availability(
        learner_id=learner.learner_id,
        day_of_week=DayOfWeek.FRIDAY,
        availability_type=AvailabilityType.AVAILABLE,
        start_time=time(18, 0),
        end_time=time(20, 0),
        available_minutes=120,
        effective_from=date(2026, 10, 1),
        effective_until=date(2026, 12, 31),
        source_type=EvidenceSource.PARENT_REPORTED,
    )

    repository = AvailabilityRepository(session)
    repository.add(availability)
    session.commit()

    loaded = repository.get(
        availability.availability_id
    )

    assert loaded is not None
    assert loaded.start_time == time(18, 0)
    assert loaded.end_time == time(20, 0)
    assert loaded.available_minutes == 120
    assert (
        loaded.source_type
        == EvidenceSource.PARENT_REPORTED
    )


def test_availability_with_unknown_learner_is_rejected(
    session: Session,
) -> None:
    availability = Availability(
        learner_id=uuid4(),
        day_of_week=DayOfWeek.WEDNESDAY,
        availability_type=AvailabilityType.AVAILABLE,
        available_minutes=60,
    )

    repository = AvailabilityRepository(session)

    with pytest.raises(IntegrityError):
        repository.add(availability)

    session.rollback()


def test_goal_and_availability_lists_are_learner_scoped(
    session: Session,
) -> None:
    first = Learner()
    second = Learner()

    learner_repository = LearnerRepository(session)
    learner_repository.add_learner(first)
    learner_repository.add_learner(second)

    goal_repository = GoalRepository(session)
    availability_repository = AvailabilityRepository(
        session
    )

    goal_repository.add(
        Goal(
            learner_id=first.learner_id,
            goal_type="routine",
            description="Birinci öğrenenin hedefi",
        )
    )

    goal_repository.add(
        Goal(
            learner_id=second.learner_id,
            goal_type="routine",
            description="İkinci öğrenenin hedefi",
        )
    )

    availability_repository.add(
        Availability(
            learner_id=first.learner_id,
            day_of_week=DayOfWeek.SATURDAY,
            availability_type=AvailabilityType.AVAILABLE,
            available_minutes=90,
        )
    )

    session.commit()

    first_goals = goal_repository.list_for_learner(
        first.learner_id
    )

    first_availability = (
        availability_repository.list_for_learner(
            first.learner_id
        )
    )

    assert len(first_goals) == 1
    assert (
        first_goals[0].description
        == "Birinci öğrenenin hedefi"
    )

    assert len(first_availability) == 1
    assert (
        first_availability[0].learner_id
        == first.learner_id
    )
