from datetime import date, datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

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


def make_context() -> tuple[Learner, LearningContext]:
    learner = Learner()

    context = LearningContext(
        learner_id=learner.learner_id,
        context_type=ContextType.SCHOOL,
        program_code="school_7",
        grade_level=7,
    )

    return learner, context


def test_assessment_is_general_not_exam_specific() -> None:
    learner, context = make_context()

    assessment = Assessment(
        learner_id=learner.learner_id,
        context_id=context.context_id,
        assessment_type="written_exam",
        assessment_name="Matematik Yazılısı",
        assessment_date=date(2026, 10, 2),
    )

    assert assessment.assessment_type == "written_exam"
    assert assessment.context_id == context.context_id


def test_school_grade_can_be_stored_without_net() -> None:
    learner, context = make_context()

    assessment = Assessment(
        learner_id=learner.learner_id,
        context_id=context.context_id,
        assessment_type="written_exam",
        assessment_name="Matematik Yazılısı",
        assessment_date=date(2026, 10, 2),
    )

    result = AssessmentResult(
        assessment_id=assessment.assessment_id,
        grade=78,
    )

    assert result.grade == 78
    assert result.net is None


def test_exam_net_can_be_stored_without_score() -> None:
    learner = Learner()

    context = LearningContext(
        learner_id=learner.learner_id,
        context_type=ContextType.ENTRANCE_EXAM,
        program_code="yks",
    )

    assessment = Assessment(
        learner_id=learner.learner_id,
        context_id=context.context_id,
        assessment_type="mock_exam",
        assessment_name="TYT Denemesi",
        assessment_date=date(2026, 10, 2),
    )

    result = AssessmentResult(
        assessment_id=assessment.assessment_id,
        area_type="exam_section",
        area_code="tyt",
        net=74,
    )

    assert result.net == 74
    assert result.score is None


def test_assessment_result_requires_at_least_one_metric() -> None:
    learner, context = make_context()

    assessment = Assessment(
        learner_id=learner.learner_id,
        context_id=context.context_id,
        assessment_type="quiz",
        assessment_name="Konu Testi",
        assessment_date=date(2026, 10, 2),
    )

    with pytest.raises(ValidationError):
        AssessmentResult(
            assessment_id=assessment.assessment_id,
        )


def test_area_type_and_area_code_must_be_given_together() -> None:
    learner, context = make_context()

    assessment = Assessment(
        learner_id=learner.learner_id,
        context_id=context.context_id,
        assessment_type="quiz",
        assessment_name="Konu Testi",
        assessment_date=date(2026, 10, 2),
    )

    with pytest.raises(ValidationError):
        AssessmentResult(
            assessment_id=assessment.assessment_id,
            area_type="subject",
            percentage=80,
        )


def test_percentage_outside_zero_to_hundred_is_rejected() -> None:
    learner, context = make_context()

    assessment = Assessment(
        learner_id=learner.learner_id,
        context_id=context.context_id,
        assessment_type="quiz",
        assessment_name="Konu Testi",
        assessment_date=date(2026, 10, 2),
    )

    with pytest.raises(ValidationError):
        AssessmentResult(
            assessment_id=assessment.assessment_id,
            percentage=120,
        )


def test_learner_reported_evidence_does_not_need_assessment() -> None:
    learner, context = make_context()

    evidence = LearningEvidence(
        learner_id=learner.learner_id,
        context_id=context.context_id,
        area_type="subject",
        area_code="mathematics",
        state=EvidenceState.WEAK,
        source_type=EvidenceSource.LEARNER_REPORTED,
    )

    assert evidence.state == EvidenceState.WEAK
    assert evidence.assessment_id is None


def test_assessment_derived_evidence_requires_assessment_id() -> None:
    learner, context = make_context()

    with pytest.raises(ValidationError):
        LearningEvidence(
            learner_id=learner.learner_id,
            context_id=context.context_id,
            area_type="subject",
            area_code="mathematics",
            state=EvidenceState.WEAK,
            source_type=EvidenceSource.ASSESSMENT_DERIVED,
        )


def test_assessment_derived_evidence_keeps_provenance() -> None:
    learner, context = make_context()

    assessment = Assessment(
        learner_id=learner.learner_id,
        context_id=context.context_id,
        assessment_type="written_exam",
        assessment_name="Matematik Yazılısı",
        assessment_date=date(2026, 10, 2),
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

    assert evidence.assessment_id == assessment.assessment_id
    assert evidence.confidence == 0.8


def test_evidence_valid_until_cannot_precede_observation() -> None:
    learner, context = make_context()

    observed_at = datetime(2026, 10, 2, tzinfo=timezone.utc)

    with pytest.raises(ValidationError):
        LearningEvidence(
            learner_id=learner.learner_id,
            context_id=context.context_id,
            area_type="skill",
            area_code="reading",
            state=EvidenceState.DEVELOPING,
            source_type=EvidenceSource.COACH_INFERRED,
            observed_at=observed_at,
            valid_until=observed_at - timedelta(days=1),
        )
