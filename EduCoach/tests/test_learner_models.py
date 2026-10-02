from datetime import date

import pytest
from pydantic import ValidationError

from educoach.models import (
    ContextType,
    EducationStatus,
    EvidenceSource,
    Learner,
    LearningContext,
)


def test_learner_defaults_are_general_not_exam_specific() -> None:
    learner = Learner()

    assert learner.education_status == EducationStatus.UNKNOWN
    assert learner.preferred_language == "tr"
    assert learner.timezone == "Europe/Istanbul"

    assert not hasattr(learner, "tyt_net")
    assert not hasattr(learner, "ayt_net")
    assert not hasattr(learner, "kpss_score")


def test_same_learner_can_have_school_and_exam_contexts() -> None:
    learner = Learner(
        display_name="Ayşe",
        education_status=EducationStatus.HIGH_SCHOOL,
    )

    school = LearningContext(
        learner_id=learner.learner_id,
        context_type=ContextType.SCHOOL,
        program_code="school_11",
        grade_level=11,
    )

    yks = LearningContext(
        learner_id=learner.learner_id,
        context_type=ContextType.ENTRANCE_EXAM,
        program_code="yks",
        exam_year=2028,
    )

    assert school.learner_id == yks.learner_id == learner.learner_id
    assert school.program_code == "school_11"
    assert yks.program_code == "yks"


@pytest.mark.parametrize("grade_level", [4, 13])
def test_grade_level_outside_supported_range_is_rejected(
    grade_level: int,
) -> None:
    learner = Learner()

    with pytest.raises(ValidationError):
        LearningContext(
            learner_id=learner.learner_id,
            context_type=ContextType.SCHOOL,
            program_code="school",
            grade_level=grade_level,
        )


def test_context_end_date_cannot_be_before_start_date() -> None:
    learner = Learner()

    with pytest.raises(ValidationError):
        LearningContext(
            learner_id=learner.learner_id,
            context_type=ContextType.ACADEMIC_EXAM,
            program_code="ales",
            started_at=date(2026, 10, 2),
            ended_at=date(2026, 10, 1),
        )


def test_evidence_source_keeps_fact_provenance_explicit() -> None:
    assert EvidenceSource.LEARNER_REPORTED == "learner_reported"
    assert EvidenceSource.ASSESSMENT_DERIVED == "assessment_derived"
    assert EvidenceSource.COACH_INFERRED == "coach_inferred"
