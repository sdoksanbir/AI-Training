import pytest
from pydantic import ValidationError

from educoach.models import (
    CoachingState,
    CoachingStatus,
    ContextType,
    EvidenceSource,
    Learner,
    LearningContext,
    Preference,
)


def make_context() -> tuple[Learner, LearningContext]:
    learner = Learner()

    context = LearningContext(
        learner_id=learner.learner_id,
        context_type=ContextType.LANGUAGE_LEARNING,
        program_code="general_english",
    )

    return learner, context


def test_global_preference_does_not_require_context() -> None:
    learner = Learner()

    preference = Preference(
        learner_id=learner.learner_id,
        preference_key="explanation_style",
        preference_value="short",
    )

    assert preference.context_id is None
    assert preference.preference_value == "short"


def test_preference_can_be_context_specific() -> None:
    learner, context = make_context()

    preference = Preference(
        learner_id=learner.learner_id,
        context_id=context.context_id,
        preference_key="session_minutes",
        preference_value=40,
    )

    assert preference.context_id == context.context_id
    assert preference.preference_value == 40


def test_preference_key_cannot_be_blank() -> None:
    learner = Learner()

    with pytest.raises(ValidationError):
        Preference(
            learner_id=learner.learner_id,
            preference_key="   ",
            preference_value=True,
        )


def test_preference_keeps_provenance() -> None:
    learner = Learner()

    preference = Preference(
        learner_id=learner.learner_id,
        preference_key="study_time",
        preference_value="evening",
        source_type=EvidenceSource.PARENT_REPORTED,
        confidence=0.9,
    )

    assert preference.source_type == EvidenceSource.PARENT_REPORTED
    assert preference.confidence == 0.9


def test_preference_confidence_must_be_between_zero_and_one() -> None:
    learner = Learner()

    with pytest.raises(ValidationError):
        Preference(
            learner_id=learner.learner_id,
            preference_key="study_time",
            preference_value="evening",
            confidence=1.2,
        )


def test_coaching_state_defaults_to_onboarding() -> None:
    learner = Learner()

    state = CoachingState(
        learner_id=learner.learner_id,
    )

    assert state.status == CoachingStatus.ONBOARDING
    assert state.context_id is None


def test_coaching_state_can_be_context_specific() -> None:
    learner, context = make_context()

    state = CoachingState(
        learner_id=learner.learner_id,
        context_id=context.context_id,
        status=CoachingStatus.ACTIVE,
        current_focus="Kelime çalışması",
    )

    assert state.context_id == context.context_id
    assert state.current_focus == "Kelime çalışması"


def test_blank_current_focus_becomes_none() -> None:
    learner = Learner()

    state = CoachingState(
        learner_id=learner.learner_id,
        current_focus="   ",
    )

    assert state.current_focus is None
