"""Typed, persisted Learner Memory read model."""

from dataclasses import dataclass

from educoach.models import (
    Assessment,
    AssessmentResult,
    Availability,
    CoachingState,
    Goal,
    Learner,
    LearningContext,
    LearningEvidence,
    Preference,
    StudyPlan,
    StudySession,
    StudyTask,
)


@dataclass(frozen=True)
class LearnerMemorySnapshot:
    learner: Learner
    contexts: tuple[LearningContext, ...]
    goals: tuple[Goal, ...]
    availability: tuple[Availability, ...]
    assessments: tuple[Assessment, ...]
    assessment_results: tuple[AssessmentResult, ...]
    learning_evidence: tuple[LearningEvidence, ...]
    study_plans: tuple[StudyPlan, ...]
    study_tasks: tuple[StudyTask, ...]
    study_sessions: tuple[StudySession, ...]
    preferences: tuple[Preference, ...]
    coaching_states: tuple[CoachingState, ...]
