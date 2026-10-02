from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from educoach.models import (
    Assessment,
    ContextType,
    EvidenceSource,
    EvidenceState,
    Goal,
    Learner,
    LearningContext,
    LearningEvidence,
)
from educoach.persistence import (
    create_schema,
    create_session_factory,
    create_sqlite_engine,
)
from educoach.repositories import (
    AssessmentRepository,
    GoalRepository,
    LearnerRepository,
    LearningEvidenceRepository,
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


def make_two_learners(
    session: Session,
) -> tuple[Learner, Learner, LearningContext]:
    first = Learner()
    second = Learner()

    second_context = LearningContext(
        learner_id=second.learner_id,
        context_type=ContextType.SCHOOL,
        program_code="school_8",
        grade_level=8,
    )

    repository = LearnerRepository(session)
    repository.add_learner(first)
    repository.add_learner(second)
    repository.add_context(second_context)

    return first, second, second_context


def test_goal_cannot_use_another_learners_context(
    session: Session,
) -> None:
    first, _, second_context = make_two_learners(
        session
    )

    goal = Goal(
        learner_id=first.learner_id,
        context_id=second_context.context_id,
        goal_type="routine",
        description="Geçersiz çapraz bağ",
    )

    with pytest.raises(IntegrityError):
        GoalRepository(session).add(goal)

    session.rollback()


def test_assessment_cannot_use_another_learners_context(
    session: Session,
) -> None:
    first, _, second_context = make_two_learners(
        session
    )

    assessment = Assessment(
        learner_id=first.learner_id,
        context_id=second_context.context_id,
        assessment_type="quiz",
        assessment_name="Geçersiz bağ",
        assessment_date=date(2026, 10, 2),
    )

    with pytest.raises(IntegrityError):
        AssessmentRepository(session).add_assessment(
            assessment
        )

    session.rollback()


def test_evidence_cannot_use_another_learners_context(
    session: Session,
) -> None:
    first, _, second_context = make_two_learners(
        session
    )

    evidence = LearningEvidence(
        learner_id=first.learner_id,
        context_id=second_context.context_id,
        area_type="subject",
        area_code="mathematics",
        state=EvidenceState.DEVELOPING,
        source_type=EvidenceSource.TEACHER_REPORTED,
    )

    with pytest.raises(IntegrityError):
        LearningEvidenceRepository(session).add(
            evidence
        )

    session.rollback()



def test_assessment_derived_evidence_cannot_reference_another_learners_assessment(
    session: Session,
) -> None:
    first = Learner()
    second = Learner()

    first_context = LearningContext(
        learner_id=first.learner_id,
        context_type=ContextType.SCHOOL,
        program_code="school_7",
        grade_level=7,
    )

    second_context = LearningContext(
        learner_id=second.learner_id,
        context_type=ContextType.SCHOOL,
        program_code="school_8",
        grade_level=8,
    )

    learner_repository = LearnerRepository(session)
    learner_repository.add_learner(first)
    learner_repository.add_learner(second)
    learner_repository.add_context(first_context)
    learner_repository.add_context(second_context)

    assessment = Assessment(
        learner_id=second.learner_id,
        context_id=second_context.context_id,
        assessment_type="quiz",
        assessment_name="İkinci öğrencinin sınavı",
        assessment_date=date(2026, 10, 2),
    )

    AssessmentRepository(session).add_assessment(
        assessment
    )

    evidence = LearningEvidence(
        learner_id=first.learner_id,
        context_id=first_context.context_id,
        area_type="subject",
        area_code="mathematics",
        state=EvidenceState.WEAK,
        source_type=EvidenceSource.ASSESSMENT_DERIVED,
        assessment_id=assessment.assessment_id,
    )

    with pytest.raises(IntegrityError):
        LearningEvidenceRepository(session).add(
            evidence
        )

    session.rollback()


def test_assessment_derived_evidence_cannot_reference_assessment_from_another_context(
    session: Session,
) -> None:
    learner = Learner()

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

    learner_repository = LearnerRepository(session)
    learner_repository.add_learner(learner)
    learner_repository.add_context(school_context)
    learner_repository.add_context(exam_context)

    assessment = Assessment(
        learner_id=learner.learner_id,
        context_id=school_context.context_id,
        assessment_type="written_exam",
        assessment_name="Okul matematik yazılısı",
        assessment_date=date(2026, 10, 2),
    )

    AssessmentRepository(session).add_assessment(
        assessment
    )

    evidence = LearningEvidence(
        learner_id=learner.learner_id,
        context_id=exam_context.context_id,
        area_type="subject",
        area_code="mathematics",
        state=EvidenceState.DEVELOPING,
        source_type=EvidenceSource.ASSESSMENT_DERIVED,
        assessment_id=assessment.assessment_id,
    )

    with pytest.raises(IntegrityError):
        LearningEvidenceRepository(session).add(
            evidence
        )

    session.rollback()
