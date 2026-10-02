from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from educoach.models import (
    Assessment,
    AssessmentResult,
    ContextType,
    EvidenceSource,
    EvidenceState,
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


def make_learner_and_context(
    session: Session,
) -> tuple[Learner, LearningContext]:
    learner = Learner()

    context = LearningContext(
        learner_id=learner.learner_id,
        context_type=ContextType.SCHOOL,
        program_code="school_8",
        grade_level=8,
    )

    repository = LearnerRepository(session)
    repository.add_learner(learner)
    repository.add_context(context)

    return learner, context


def test_assessment_round_trip(
    session: Session,
) -> None:
    learner, context = make_learner_and_context(
        session
    )

    assessment = Assessment(
        learner_id=learner.learner_id,
        context_id=context.context_id,
        assessment_type="written_exam",
        assessment_name="Matematik Yazılısı",
        assessment_date=date(2026, 10, 2),
        source_type=EvidenceSource.TEACHER_REPORTED,
        notes="Birinci yazılı",
    )

    repository = AssessmentRepository(session)
    repository.add_assessment(assessment)
    session.commit()

    loaded = repository.get_assessment(
        assessment.assessment_id
    )

    assert loaded is not None
    assert loaded.assessment_id == assessment.assessment_id
    assert loaded.learner_id == learner.learner_id
    assert loaded.context_id == context.context_id
    assert loaded.assessment_name == "Matematik Yazılısı"
    assert (
        loaded.source_type
        == EvidenceSource.TEACHER_REPORTED
    )


def test_assessment_with_unknown_learner_is_rejected(
    session: Session,
) -> None:
    _, context = make_learner_and_context(session)

    assessment = Assessment(
        learner_id=uuid4(),
        context_id=context.context_id,
        assessment_type="quiz",
        assessment_name="Test",
        assessment_date=date(2026, 10, 2),
    )

    with pytest.raises(IntegrityError):
        AssessmentRepository(session).add_assessment(
            assessment
        )

    session.rollback()


def test_assessment_with_unknown_context_is_rejected(
    session: Session,
) -> None:
    learner = Learner()
    LearnerRepository(session).add_learner(learner)

    assessment = Assessment(
        learner_id=learner.learner_id,
        context_id=uuid4(),
        assessment_type="quiz",
        assessment_name="Test",
        assessment_date=date(2026, 10, 2),
    )

    with pytest.raises(IntegrityError):
        AssessmentRepository(session).add_assessment(
            assessment
        )

    session.rollback()


def test_assessment_result_round_trip(
    session: Session,
) -> None:
    learner, context = make_learner_and_context(
        session
    )

    assessment = Assessment(
        learner_id=learner.learner_id,
        context_id=context.context_id,
        assessment_type="mock_exam",
        assessment_name="Deneme",
        assessment_date=date(2026, 10, 2),
    )

    repository = AssessmentRepository(session)
    repository.add_assessment(assessment)

    result = AssessmentResult(
        assessment_id=assessment.assessment_id,
        area_type="subject",
        area_code="mathematics",
        correct=15,
        incorrect=3,
        blank=2,
        percentage=75,
        duration_minutes=40,
    )

    repository.add_result(result)
    session.commit()

    loaded = repository.get_result(
        result.assessment_result_id
    )

    assert loaded is not None
    assert loaded.assessment_id == assessment.assessment_id
    assert loaded.correct == 15
    assert loaded.incorrect == 3
    assert loaded.blank == 2
    assert loaded.percentage == 75


def test_result_with_unknown_assessment_is_rejected(
    session: Session,
) -> None:
    result = AssessmentResult(
        assessment_id=uuid4(),
        score=80,
    )

    with pytest.raises(IntegrityError):
        AssessmentRepository(session).add_result(result)

    session.rollback()


def test_non_assessment_evidence_round_trip(
    session: Session,
) -> None:
    learner, context = make_learner_and_context(
        session
    )

    evidence = LearningEvidence(
        learner_id=learner.learner_id,
        context_id=context.context_id,
        area_type="subject",
        area_code="mathematics",
        state=EvidenceState.DEVELOPING,
        source_type=EvidenceSource.LEARNER_REPORTED,
        confidence=0.6,
    )

    repository = LearningEvidenceRepository(session)
    repository.add(evidence)
    session.commit()

    loaded = repository.get(evidence.evidence_id)

    assert loaded is not None
    assert loaded.assessment_id is None
    assert loaded.state == EvidenceState.DEVELOPING
    assert loaded.confidence == 0.6


def test_assessment_derived_evidence_round_trip(
    session: Session,
) -> None:
    learner, context = make_learner_and_context(
        session
    )

    assessment = Assessment(
        learner_id=learner.learner_id,
        context_id=context.context_id,
        assessment_type="written_exam",
        assessment_name="Matematik Yazılısı",
        assessment_date=date(2026, 10, 2),
    )

    AssessmentRepository(session).add_assessment(
        assessment
    )

    evidence = LearningEvidence(
        learner_id=learner.learner_id,
        context_id=context.context_id,
        area_type="subject",
        area_code="mathematics",
        state=EvidenceState.WEAK,
        source_type=EvidenceSource.ASSESSMENT_DERIVED,
        assessment_id=assessment.assessment_id,
        confidence=0.9,
    )

    repository = LearningEvidenceRepository(session)
    repository.add(evidence)
    session.commit()

    loaded = repository.get(evidence.evidence_id)

    assert loaded is not None
    assert loaded.assessment_id == assessment.assessment_id
    assert (
        loaded.source_type
        == EvidenceSource.ASSESSMENT_DERIVED
    )


def test_assessment_derived_evidence_with_unknown_assessment_is_rejected(
    session: Session,
) -> None:
    learner, context = make_learner_and_context(
        session
    )

    evidence = LearningEvidence(
        learner_id=learner.learner_id,
        context_id=context.context_id,
        area_type="subject",
        area_code="mathematics",
        state=EvidenceState.WEAK,
        source_type=EvidenceSource.ASSESSMENT_DERIVED,
        assessment_id=uuid4(),
    )

    with pytest.raises(IntegrityError):
        LearningEvidenceRepository(session).add(
            evidence
        )

    session.rollback()


def test_results_are_scoped_to_assessment(
    session: Session,
) -> None:
    learner, context = make_learner_and_context(
        session
    )

    first = Assessment(
        learner_id=learner.learner_id,
        context_id=context.context_id,
        assessment_type="quiz",
        assessment_name="Birinci",
        assessment_date=date(2026, 10, 1),
    )

    second = Assessment(
        learner_id=learner.learner_id,
        context_id=context.context_id,
        assessment_type="quiz",
        assessment_name="İkinci",
        assessment_date=date(2026, 10, 2),
    )

    repository = AssessmentRepository(session)
    repository.add_assessment(first)
    repository.add_assessment(second)

    repository.add_result(
        AssessmentResult(
            assessment_id=first.assessment_id,
            score=70,
        )
    )

    repository.add_result(
        AssessmentResult(
            assessment_id=second.assessment_id,
            score=90,
        )
    )

    session.commit()

    results = repository.list_results(
        first.assessment_id
    )

    assert len(results) == 1
    assert results[0].score == 70


def test_evidence_list_is_learner_scoped(
    session: Session,
) -> None:
    first, first_context = make_learner_and_context(
        session
    )

    second = Learner()
    second_context = LearningContext(
        learner_id=second.learner_id,
        context_type=ContextType.LANGUAGE_LEARNING,
        program_code="general_english",
    )

    learner_repository = LearnerRepository(session)
    learner_repository.add_learner(second)
    learner_repository.add_context(second_context)

    repository = LearningEvidenceRepository(session)

    repository.add(
        LearningEvidence(
            learner_id=first.learner_id,
            context_id=first_context.context_id,
            area_type="subject",
            area_code="mathematics",
            state=EvidenceState.ADEQUATE,
            source_type=EvidenceSource.TEACHER_REPORTED,
        )
    )

    repository.add(
        LearningEvidence(
            learner_id=second.learner_id,
            context_id=second_context.context_id,
            area_type="skill",
            area_code="reading",
            state=EvidenceState.DEVELOPING,
            source_type=EvidenceSource.LEARNER_REPORTED,
        )
    )

    session.commit()

    evidence = repository.list_for_learner(
        first.learner_id
    )

    assert len(evidence) == 1
    assert evidence[0].area_code == "mathematics"
