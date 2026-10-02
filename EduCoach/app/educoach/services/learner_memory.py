"""Learner Memory application service."""

from collections.abc import Iterable

from sqlalchemy.orm import Session, sessionmaker

from educoach.models import (
    Assessment,
    AssessmentResult,
    EvidenceSource,
    Learner,
    LearningContext,
    LearningEvidence,
)
from educoach.repositories import (
    AssessmentRepository,
    LearnerRepository,
    LearningEvidenceRepository,
)


class LearnerMemoryService:
    """Coordinates transactional Learner Memory operations."""

    def __init__(
        self,
        session_factory: sessionmaker[Session],
    ) -> None:
        self.session_factory = session_factory

    def register_learner(
        self,
        learner: Learner,
        contexts: Iterable[LearningContext] = (),
    ) -> Learner:
        context_items = tuple(contexts)

        for context in context_items:
            if context.learner_id != learner.learner_id:
                raise ValueError(
                    "LearningContext learner_id, kayıt edilen "
                    "Learner ile aynı olmalıdır"
                )

        with self.session_factory() as session:
            repository = LearnerRepository(session)

            with session.begin():
                repository.add_learner(learner)

                for context in context_items:
                    repository.add_context(context)

        return learner

    def record_assessment(
        self,
        assessment: Assessment,
        results: Iterable[AssessmentResult] = (),
        evidence: Iterable[LearningEvidence] = (),
    ) -> Assessment:
        result_items = tuple(results)
        evidence_items = tuple(evidence)

        for result in result_items:
            if result.assessment_id != assessment.assessment_id:
                raise ValueError(
                    "AssessmentResult assessment_id, kayıt edilen "
                    "Assessment ile aynı olmalıdır"
                )

        for item in evidence_items:
            if item.source_type != EvidenceSource.ASSESSMENT_DERIVED:
                raise ValueError(
                    "record_assessment yalnız assessment_derived "
                    "LearningEvidence kabul eder"
                )

            if item.learner_id != assessment.learner_id:
                raise ValueError(
                    "LearningEvidence learner_id, Assessment learner_id "
                    "ile aynı olmalıdır"
                )

            if item.context_id != assessment.context_id:
                raise ValueError(
                    "LearningEvidence context_id, Assessment context_id "
                    "ile aynı olmalıdır"
                )

            if item.assessment_id != assessment.assessment_id:
                raise ValueError(
                    "LearningEvidence assessment_id, kayıt edilen "
                    "Assessment ile aynı olmalıdır"
                )

        with self.session_factory() as session:
            assessment_repository = AssessmentRepository(
                session
            )
            evidence_repository = LearningEvidenceRepository(
                session
            )

            with session.begin():
                assessment_repository.add_assessment(
                    assessment
                )

                for result in result_items:
                    assessment_repository.add_result(
                        result
                    )

                for item in evidence_items:
                    evidence_repository.add(item)

        return assessment
