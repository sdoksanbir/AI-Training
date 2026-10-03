"""Deterministic projection of recorded assessment truth."""

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from educoach.models import Assessment, AssessmentResult, EvidenceSource
from educoach.services.snapshot import LearnerMemorySnapshot


@dataclass(frozen=True)
class RecordedAssessmentResultFact:
    assessment_result_id: UUID
    assessment_id: UUID
    context_id: UUID
    area_type: str | None
    area_code: str | None
    correct: int | None
    incorrect: int | None
    blank: int | None
    net: float | None
    score: float | None
    percentage: float | None
    grade: float | None
    duration_minutes: int | None


@dataclass(frozen=True)
class RecordedAssessmentFact:
    assessment_id: UUID
    learner_id: UUID
    context_id: UUID
    assessment_type: str
    assessment_name: str
    assessment_date: date
    source_type: EvidenceSource
    results: tuple[RecordedAssessmentResultFact, ...]


@dataclass(frozen=True)
class AssessmentFacts:
    assessments: tuple[RecordedAssessmentFact, ...]


def project_assessment_facts(
    snapshot: LearnerMemorySnapshot,
) -> AssessmentFacts:
    """Return recorded assessment values without conversions or inference."""

    assessments = _index_assessments(snapshot)
    results_by_assessment: dict[UUID, list[AssessmentResult]] = {
        assessment_id: [] for assessment_id in assessments
    }
    result_ids: set[UUID] = set()

    for result in snapshot.assessment_results:
        if result.assessment_result_id in result_ids:
            raise ValueError(
                "snapshot cannot contain duplicate assessment_result_id values"
            )
        result_ids.add(result.assessment_result_id)
        if result.assessment_id not in assessments:
            raise ValueError(
                "assessment result must reference a snapshot assessment"
            )
        results_by_assessment[result.assessment_id].append(result)

    facts = tuple(
        _project_assessment_fact(
            assessment,
            results_by_assessment[assessment.assessment_id],
        )
        for assessment in sorted(
            assessments.values(),
            key=lambda item: str(item.assessment_id),
        )
    )
    return AssessmentFacts(assessments=facts)


def _index_assessments(
    snapshot: LearnerMemorySnapshot,
) -> dict[UUID, Assessment]:
    indexed: dict[UUID, Assessment] = {}
    learner_id = snapshot.learner.learner_id

    for assessment in snapshot.assessments:
        if assessment.assessment_id in indexed:
            raise ValueError(
                "snapshot cannot contain duplicate assessment_id values"
            )
        if assessment.learner_id != learner_id:
            raise ValueError("assessment must belong to the snapshot learner")
        indexed[assessment.assessment_id] = assessment

    return indexed


def _project_assessment_fact(
    assessment: Assessment,
    results: list[AssessmentResult],
) -> RecordedAssessmentFact:
    ordered_results = sorted(
        results,
        key=lambda item: str(item.assessment_result_id),
    )
    return RecordedAssessmentFact(
        assessment_id=assessment.assessment_id,
        learner_id=assessment.learner_id,
        context_id=assessment.context_id,
        assessment_type=assessment.assessment_type,
        assessment_name=assessment.assessment_name,
        assessment_date=assessment.assessment_date,
        source_type=assessment.source_type,
        results=tuple(
            _project_result_fact(result, assessment.context_id)
            for result in ordered_results
        ),
    )


def _project_result_fact(
    result: AssessmentResult,
    context_id: UUID,
) -> RecordedAssessmentResultFact:
    return RecordedAssessmentResultFact(
        assessment_result_id=result.assessment_result_id,
        assessment_id=result.assessment_id,
        context_id=context_id,
        area_type=result.area_type,
        area_code=result.area_code,
        correct=result.correct,
        incorrect=result.incorrect,
        blank=result.blank,
        net=result.net,
        score=result.score,
        percentage=result.percentage,
        grade=result.grade,
        duration_minutes=result.duration_minutes,
    )
