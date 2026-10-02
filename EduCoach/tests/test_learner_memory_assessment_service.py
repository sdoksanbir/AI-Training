from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

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
    LearningEvidenceRepository,
)
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


def register_learner_with_context(
    factory: sessionmaker[Session],
) -> tuple[Learner, LearningContext]:
    learner = Learner()

    context = LearningContext(
        learner_id=learner.learner_id,
        context_type=ContextType.SCHOOL,
        program_code="school_8",
        grade_level=8,
    )

    LearnerMemoryService(factory).register_learner(
        learner,
        [context],
    )

    return learner, context


def test_record_assessment_commits_assessment_results_and_evidence_together(
    session_factory_fixture: sessionmaker[Session],
) -> None:
    learner, context = register_learner_with_context(
        session_factory_fixture
    )

    assessment = Assessment(
        learner_id=learner.learner_id,
        context_id=context.context_id,
        assessment_type="written_exam",
        assessment_name="Matematik YazÄ±lÄ±sÄ±",
        assessment_date=date(2026, 10, 2),
    )

    first_result = AssessmentResult(
        assessment_id=assessment.assessment_id,
        area_type="subject",
        area_code="mathematics",
        score=78,
    )

    second_result = AssessmentResult(
        assessment_id=assessment.assessment_id,
        area_type="skill",
        area_code="problem_solving",
        percentage=65,
    )

    evidence = LearningEvidence(
        learner_id=learner.learner_id,
        context_id=context.context_id,
        area_type="subject",
        area_code="mathematics",
        state=EvidenceState.DEVELOPING,
        source_type=EvidenceSource.ASSESSMENT_DERIVED,
        assessment_id=assessment.assessment_id,
        confidence=0.8,
    )

    service = LearnerMemoryService(
        session_factory_fixture
    )

    service.record_assessment(
        assessment,
        results=[first_result, second_result],
        evidence=[evidence],
    )

    with session_factory_fixture() as session:
        assessment_repository = AssessmentRepository(
            session
        )
        evidence_repository = LearningEvidenceRepository(
            session
        )

        loaded_assessment = (
            assessment_repository.get_assessment(
                assessment.assessment_id
            )
        )

        loaded_results = (
            assessment_repository.list_results(
                assessment.assessment_id
            )
        )

        loaded_evidence = (
            evidence_repository.list_for_learner(
                learner.learner_id
            )
        )

    assert loaded_assessment is not None
    assert len(loaded_results) == 2
    assert len(loaded_evidence) == 1
    assert (
        loaded_evidence[0].assessment_id
        == assessment.assessment_id
    )


def test_record_assessment_rejects_result_for_another_assessment(
    session_factory_fixture: sessionmaker[Session],
) -> None:
    learner, context = register_learner_with_context(
        session_factory_fixture
    )

    assessment = Assessment(
        learner_id=learner.learner_id,
        context_id=context.context_id,
        assessment_type="quiz",
        assessment_name="Konu Testi",
        assessment_date=date(2026, 10, 2),
    )

    result = AssessmentResult(
        assessment_id=uuid4(),
        score=80,
    )

    service = LearnerMemoryService(
        session_factory_fixture
    )

    with pytest.raises(ValueError):
        service.record_assessment(
            assessment,
            results=[result],
        )

    with session_factory_fixture() as session:
        loaded = AssessmentRepository(
            session
        ).get_assessment(
            assessment.assessment_id
        )

    assert loaded is None


def test_record_assessment_rejects_evidence_for_another_learner(
    session_factory_fixture: sessionmaker[Session],
) -> None:
    learner, context = register_learner_with_context(
        session_factory_fixture
    )

    assessment = Assessment(
        learner_id=learner.learner_id,
        context_id=context.context_id,
        assessment_type="quiz",
        assessment_name="Konu Testi",
        assessment_date=date(2026, 10, 2),
    )

    evidence = LearningEvidence(
        learner_id=uuid4(),
        context_id=context.context_id,
        area_type="subject",
        area_code="mathematics",
        state=EvidenceState.WEAK,
        source_type=EvidenceSource.ASSESSMENT_DERIVED,
        assessment_id=assessment.assessment_id,
    )

    service = LearnerMemoryService(
        session_factory_fixture
    )

    with pytest.raises(ValueError):
        service.record_assessment(
            assessment,
            evidence=[evidence],
        )

    with session_factory_fixture() as session:
        loaded = AssessmentRepository(
            session
        ).get_assessment(
            assessment.assessment_id
        )

    assert loaded is None


def test_record_assessment_rejects_evidence_for_another_assessment(
    session_factory_fixture: sessionmaker[Session],
) -> None:
    learner, context = register_learner_with_context(
        session_factory_fixture
    )

    assessment = Assessment(
        learner_id=learner.learner_id,
        context_id=context.context_id,
        assessment_type="quiz",
        assessment_name="Konu Testi",
        assessment_date=date(2026, 10, 2),
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

    service = LearnerMemoryService(
        session_factory_fixture
    )

    with pytest.raises(ValueError):
        service.record_assessment(
            assessment,
            evidence=[evidence],
        )

    with session_factory_fixture() as session:
        loaded = AssessmentRepository(
            session
        ).get_assessment(
            assessment.assessment_id
        )

    assert loaded is None


def test_record_assessment_rolls_back_everything_when_result_insert_fails(
    session_factory_fixture: sessionmaker[Session],
) -> None:
    learner, context = register_learner_with_context(
        session_factory_fixture
    )

    assessment = Assessment(
        learner_id=learner.learner_id,
        context_id=context.context_id,
        assessment_type="mock_exam",
        assessment_name="Deneme",
        assessment_date=date(2026, 10, 2),
    )

    duplicated_result_id = uuid4()

    first_result = AssessmentResult(
        assessment_result_id=duplicated_result_id,
        assessment_id=assessment.assessment_id,
        score=70,
    )

    second_result = AssessmentResult(
        assessment_result_id=duplicated_result_id,
        assessment_id=assessment.assessment_id,
        score=80,
    )

    service = LearnerMemoryService(
        session_factory_fixture
    )

    with pytest.raises(IntegrityError):
        service.record_assessment(
            assessment,
            results=[first_result, second_result],
        )

    with session_factory_fixture() as session:
        repository = AssessmentRepository(session)

        loaded_assessment = repository.get_assessment(
            assessment.assessment_id
        )

        loaded_results = repository.list_results(
            assessment.assessment_id
        )

    assert loaded_assessment is None
    assert loaded_results == []



def test_record_assessment_rejects_non_assessment_derived_evidence(
    session_factory_fixture: sessionmaker[Session],
) -> None:
    learner, context = register_learner_with_context(
        session_factory_fixture
    )

    assessment = Assessment(
        learner_id=learner.learner_id,
        context_id=context.context_id,
        assessment_type="quiz",
        assessment_name="Konu Testi",
        assessment_date=date(2026, 10, 2),
    )

    evidence = LearningEvidence(
        learner_id=learner.learner_id,
        context_id=context.context_id,
        area_type="subject",
        area_code="mathematics",
        state=EvidenceState.DEVELOPING,
        source_type=EvidenceSource.TEACHER_REPORTED,
        assessment_id=assessment.assessment_id,
    )

    service = LearnerMemoryService(
        session_factory_fixture
    )

    with pytest.raises(ValueError):
        service.record_assessment(
            assessment,
            evidence=[evidence],
        )

    with session_factory_fixture() as session:
        loaded = AssessmentRepository(
            session
        ).get_assessment(
            assessment.assessment_id
        )

    assert loaded is None


def test_record_assessment_rolls_back_everything_when_evidence_insert_fails(
    session_factory_fixture: sessionmaker[Session],
) -> None:
    learner, context = register_learner_with_context(
        session_factory_fixture
    )

    assessment = Assessment(
        learner_id=learner.learner_id,
        context_id=context.context_id,
        assessment_type="written_exam",
        assessment_name="Matematik Yazılısı",
        assessment_date=date(2026, 10, 2),
    )

    result = AssessmentResult(
        assessment_id=assessment.assessment_id,
        score=75,
    )

    duplicated_evidence_id = uuid4()

    first_evidence = LearningEvidence(
        evidence_id=duplicated_evidence_id,
        learner_id=learner.learner_id,
        context_id=context.context_id,
        area_type="subject",
        area_code="mathematics",
        state=EvidenceState.DEVELOPING,
        source_type=EvidenceSource.ASSESSMENT_DERIVED,
        assessment_id=assessment.assessment_id,
    )

    second_evidence = LearningEvidence(
        evidence_id=duplicated_evidence_id,
        learner_id=learner.learner_id,
        context_id=context.context_id,
        area_type="skill",
        area_code="problem_solving",
        state=EvidenceState.WEAK,
        source_type=EvidenceSource.ASSESSMENT_DERIVED,
        assessment_id=assessment.assessment_id,
    )

    service = LearnerMemoryService(
        session_factory_fixture
    )

    with pytest.raises(IntegrityError):
        service.record_assessment(
            assessment,
            results=[result],
            evidence=[
                first_evidence,
                second_evidence,
            ],
        )

    with session_factory_fixture() as session:
        assessment_repository = AssessmentRepository(
            session
        )
        evidence_repository = LearningEvidenceRepository(
            session
        )

        loaded_assessment = (
            assessment_repository.get_assessment(
                assessment.assessment_id
            )
        )

        loaded_results = (
            assessment_repository.list_results(
                assessment.assessment_id
            )
        )

        loaded_evidence = (
            evidence_repository.list_for_learner(
                learner.learner_id
            )
        )

    assert loaded_assessment is None
    assert loaded_results == []
    assert loaded_evidence == []
