from dataclasses import FrozenInstanceError
from datetime import date
from uuid import UUID, uuid4

import pytest

from educoach.models import Assessment, AssessmentResult, EvidenceSource, Learner
from educoach.rules import (
    AssessmentFacts,
    RecordedAssessmentFact,
    RecordedAssessmentResultFact,
    project_assessment_facts,
)
from educoach.services.snapshot import LearnerMemorySnapshot


def make_assessment(
    learner: Learner,
    *,
    assessment_id: UUID | None = None,
    context_id: UUID | None = None,
) -> Assessment:
    values = {
        "learner_id": learner.learner_id,
        "context_id": context_id or uuid4(),
        "assessment_type": "mock_exam",
        "assessment_name": "Recorded exam",
        "assessment_date": date(2026, 10, 5),
    }
    if assessment_id is not None:
        values["assessment_id"] = assessment_id
    return Assessment(**values)


def make_result(
    assessment: Assessment,
    *,
    result_id: UUID | None = None,
    **metrics,
) -> AssessmentResult:
    values = {
        "assessment_id": assessment.assessment_id,
        "net": 10.0,
    }
    values.update(metrics)
    if result_id is not None:
        values["assessment_result_id"] = result_id
    return AssessmentResult(**values)


def make_snapshot(
    learner: Learner,
    *,
    assessments: tuple[Assessment, ...] = (),
    results: tuple[AssessmentResult, ...] = (),
) -> LearnerMemorySnapshot:
    return LearnerMemorySnapshot(
        learner=learner,
        contexts=(),
        goals=(),
        availability=(),
        assessments=assessments,
        assessment_results=results,
        learning_evidence=(),
        study_plans=(),
        study_tasks=(),
        study_sessions=(),
        preferences=(),
        coaching_states=(),
    )


def test_projection_preserves_only_recorded_metric_values() -> None:
    learner = Learner()
    assessment = make_assessment(learner)
    result = make_result(
        assessment,
        area_type="section",
        area_code="tyt",
        correct=30,
        incorrect=6,
        blank=4,
        net=28.5,
        score=410.25,
        percentage=75,
        grade=80,
        duration_minutes=120,
    )

    fact = project_assessment_facts(
        make_snapshot(
            learner,
            assessments=(assessment,),
            results=(result,),
        )
    ).assessments[0].results[0]

    assert fact == RecordedAssessmentResultFact(
        assessment_result_id=result.assessment_result_id,
        assessment_id=assessment.assessment_id,
        context_id=assessment.context_id,
        area_type="section",
        area_code="tyt",
        correct=30,
        incorrect=6,
        blank=4,
        net=28.5,
        score=410.25,
        percentage=75,
        grade=80,
        duration_minutes=120,
    )


def test_assessment_without_results_has_empty_recorded_results() -> None:
    learner = Learner()
    assessment = make_assessment(learner)

    facts = project_assessment_facts(
        make_snapshot(learner, assessments=(assessment,))
    )

    assert facts.assessments[0].results == ()
    assert facts.assessments[0].source_type == EvidenceSource.LEARNER_REPORTED


def test_recorded_net_does_not_create_score() -> None:
    learner = Learner()
    assessment = make_assessment(learner)
    result = make_result(assessment, net=74, score=None)

    fact = project_assessment_facts(
        make_snapshot(learner, assessments=(assessment,), results=(result,))
    ).assessments[0].results[0]

    assert fact.net == 74
    assert fact.score is None


def test_recorded_score_does_not_create_net() -> None:
    learner = Learner()
    assessment = make_assessment(learner)
    result = make_result(assessment, net=None, score=410)

    fact = project_assessment_facts(
        make_snapshot(learner, assessments=(assessment,), results=(result,))
    ).assessments[0].results[0]

    assert fact.score == 410
    assert fact.net is None


def test_multiple_results_remain_separate_and_deterministic() -> None:
    learner = Learner()
    assessment = make_assessment(learner)
    later = make_result(assessment, result_id=UUID(int=2), net=20)
    earlier = make_result(assessment, result_id=UUID(int=1), score=300, net=None)

    results = project_assessment_facts(
        make_snapshot(
            learner,
            assessments=(assessment,),
            results=(later, earlier),
        )
    ).assessments[0].results

    assert tuple(result.assessment_result_id for result in results) == (
        earlier.assessment_result_id,
        later.assessment_result_id,
    )
    assert (results[0].score, results[0].net) == (300, None)
    assert (results[1].score, results[1].net) == (None, 20)


def test_duplicate_assessment_id_is_rejected() -> None:
    learner = Learner()
    assessment_id = uuid4()

    with pytest.raises(ValueError, match="duplicate assessment_id"):
        project_assessment_facts(
            make_snapshot(
                learner,
                assessments=(
                    make_assessment(learner, assessment_id=assessment_id),
                    make_assessment(learner, assessment_id=assessment_id),
                ),
            )
        )


def test_duplicate_assessment_result_id_is_rejected() -> None:
    learner = Learner()
    assessment = make_assessment(learner)
    result_id = uuid4()

    with pytest.raises(ValueError, match="duplicate assessment_result_id"):
        project_assessment_facts(
            make_snapshot(
                learner,
                assessments=(assessment,),
                results=(
                    make_result(assessment, result_id=result_id),
                    make_result(assessment, result_id=result_id),
                ),
            )
        )


def test_orphan_assessment_result_is_rejected() -> None:
    learner = Learner()
    missing_assessment = make_assessment(learner)

    with pytest.raises(ValueError, match="snapshot assessment"):
        project_assessment_facts(
            make_snapshot(
                learner,
                results=(make_result(missing_assessment),),
            )
        )


def test_assessment_for_another_learner_is_rejected() -> None:
    learner = Learner()
    assessment = make_assessment(Learner())

    with pytest.raises(ValueError, match="snapshot learner"):
        project_assessment_facts(
            make_snapshot(learner, assessments=(assessment,))
        )


def test_assessment_facts_are_immutable() -> None:
    learner = Learner()
    assessment = make_assessment(learner)
    facts = project_assessment_facts(
        make_snapshot(learner, assessments=(assessment,))
    )

    assert isinstance(facts, AssessmentFacts)
    assert isinstance(facts.assessments[0], RecordedAssessmentFact)
    with pytest.raises(FrozenInstanceError):
        facts.assessments = ()
