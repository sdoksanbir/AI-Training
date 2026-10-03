"""Minimal immutable projection of trustworthy learner facts."""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from uuid import UUID

from educoach.models import (
    CoachingStatus,
    ContextStatus,
    ContextType,
    EducationStatus,
    EvidenceSource,
    EvidenceState,
    GoalPriority,
    GoalStatus,
)
from educoach.services.snapshot import LearnerMemorySnapshot

from .assessment_facts import AssessmentFacts, project_assessment_facts
from .availability import (
    TimeBudgetResolutionStatus,
    resolve_daily_time_budget,
)
from .planned_actual import PlannedActualFacts, project_planned_actual_facts


class KnownFactKind(StrEnum):
    EXPLICIT = "explicit"
    DERIVED = "derived"
    INFERRED = "inferred"
    UNCERTAIN = "uncertain"


@dataclass(frozen=True)
class KnownLearnerFact:
    learner_id: UUID
    display_name: str | None
    education_status: EducationStatus
    preferred_language: str
    timezone: str
    kind: KnownFactKind = KnownFactKind.EXPLICIT


@dataclass(frozen=True)
class KnownContextFact:
    context_id: UUID
    context_type: ContextType
    program_code: str
    grade_level: int | None
    track: str | None
    exam_year: int | None
    status: ContextStatus
    kind: KnownFactKind = KnownFactKind.EXPLICIT


@dataclass(frozen=True)
class KnownGoalFact:
    goal_id: UUID
    context_id: UUID | None
    goal_type: str
    description: str
    target_value: float | None
    target_unit: str | None
    target_date: date | None
    priority: GoalPriority
    status: GoalStatus
    kind: KnownFactKind = KnownFactKind.EXPLICIT


@dataclass(frozen=True)
class KnownPreferenceFact:
    preference_id: UUID
    context_id: UUID | None
    preference_key: str
    preference_value: str | int | float | bool
    source_type: EvidenceSource
    confidence: float | None
    kind: KnownFactKind


@dataclass(frozen=True)
class KnownEvidenceFact:
    evidence_id: UUID
    context_id: UUID
    area_type: str
    area_code: str
    state: EvidenceState
    source_type: EvidenceSource
    confidence: float | None
    assessment_id: UUID | None
    kind: KnownFactKind


@dataclass(frozen=True)
class KnownCoachingStateFact:
    state_id: UUID
    context_id: UUID | None
    status: CoachingStatus
    current_focus: str | None
    kind: KnownFactKind = KnownFactKind.EXPLICIT


@dataclass(frozen=True)
class KnownAvailabilityFact:
    target_date: date
    status: TimeBudgetResolutionStatus
    available_minutes: int | None
    kind: KnownFactKind


@dataclass(frozen=True)
class KnownFactsProjection:
    learner: KnownLearnerFact
    contexts: tuple[KnownContextFact, ...]
    goals: tuple[KnownGoalFact, ...]
    preferences: tuple[KnownPreferenceFact, ...]
    learning_evidence: tuple[KnownEvidenceFact, ...]
    coaching_states: tuple[KnownCoachingStateFact, ...]
    availability: KnownAvailabilityFact
    assessments: AssessmentFacts
    planned_actual: PlannedActualFacts
    planned_actual_kind: KnownFactKind


def project_known_facts(
    snapshot: LearnerMemorySnapshot,
    target_date: date,
) -> KnownFactsProjection:
    """Project recorded and calculable facts without creating missing values."""

    context_ids = _validate_snapshot_scope(snapshot)
    budget = resolve_daily_time_budget(snapshot.availability, target_date)
    availability_kind = (
        KnownFactKind.DERIVED
        if budget.status == TimeBudgetResolutionStatus.RESOLVED
        else KnownFactKind.UNCERTAIN
    )

    return KnownFactsProjection(
        learner=KnownLearnerFact(
            learner_id=snapshot.learner.learner_id,
            display_name=snapshot.learner.display_name,
            education_status=snapshot.learner.education_status,
            preferred_language=snapshot.learner.preferred_language,
            timezone=snapshot.learner.timezone,
        ),
        contexts=tuple(
            KnownContextFact(
                context_id=context.context_id,
                context_type=context.context_type,
                program_code=context.program_code,
                grade_level=context.grade_level,
                track=context.track,
                exam_year=context.exam_year,
                status=context.status,
            )
            for context in sorted(
                snapshot.contexts,
                key=lambda item: str(item.context_id),
            )
        ),
        goals=tuple(
            KnownGoalFact(
                goal_id=goal.goal_id,
                context_id=goal.context_id,
                goal_type=goal.goal_type,
                description=goal.description,
                target_value=goal.target_value,
                target_unit=goal.target_unit,
                target_date=goal.target_date,
                priority=goal.priority,
                status=goal.status,
            )
            for goal in sorted(snapshot.goals, key=lambda item: str(item.goal_id))
        ),
        preferences=tuple(
            KnownPreferenceFact(
                preference_id=preference.preference_id,
                context_id=preference.context_id,
                preference_key=preference.preference_key,
                preference_value=preference.preference_value,
                source_type=preference.source_type,
                confidence=preference.confidence,
                kind=_kind_from_source(preference.source_type),
            )
            for preference in sorted(
                snapshot.preferences,
                key=lambda item: str(item.preference_id),
            )
        ),
        learning_evidence=tuple(
            KnownEvidenceFact(
                evidence_id=evidence.evidence_id,
                context_id=evidence.context_id,
                area_type=evidence.area_type,
                area_code=evidence.area_code,
                state=evidence.state,
                source_type=evidence.source_type,
                confidence=evidence.confidence,
                assessment_id=evidence.assessment_id,
                kind=(
                    KnownFactKind.UNCERTAIN
                    if evidence.state == EvidenceState.UNKNOWN
                    else _kind_from_source(evidence.source_type)
                ),
            )
            for evidence in sorted(
                snapshot.learning_evidence,
                key=lambda item: str(item.evidence_id),
            )
        ),
        coaching_states=tuple(
            KnownCoachingStateFact(
                state_id=state.state_id,
                context_id=state.context_id,
                status=state.status,
                current_focus=state.current_focus,
            )
            for state in sorted(
                snapshot.coaching_states,
                key=lambda item: str(item.state_id),
            )
        ),
        availability=KnownAvailabilityFact(
            target_date=budget.target_date,
            status=budget.status,
            available_minutes=budget.available_minutes,
            kind=availability_kind,
        ),
        assessments=project_assessment_facts(snapshot),
        planned_actual=project_planned_actual_facts(snapshot),
        planned_actual_kind=KnownFactKind.DERIVED,
    )


def _validate_snapshot_scope(snapshot: LearnerMemorySnapshot) -> set[UUID]:
    learner_id = snapshot.learner.learner_id
    context_ids: set[UUID] = set()

    for context in snapshot.contexts:
        if context.context_id in context_ids:
            raise ValueError("snapshot cannot contain duplicate context_id values")
        if context.learner_id != learner_id:
            raise ValueError("context must belong to the snapshot learner")
        context_ids.add(context.context_id)

    _validate_scoped_records(snapshot.goals, learner_id, context_ids, "goal")
    _validate_scoped_records(
        snapshot.preferences,
        learner_id,
        context_ids,
        "preference",
    )
    _validate_scoped_records(
        snapshot.coaching_states,
        learner_id,
        context_ids,
        "coaching state",
    )
    _validate_scoped_records(
        snapshot.learning_evidence,
        learner_id,
        context_ids,
        "learning evidence",
    )

    for availability in snapshot.availability:
        if availability.learner_id != learner_id:
            raise ValueError("availability must belong to the snapshot learner")
    for session in snapshot.study_sessions:
        if session.learner_id != learner_id:
            raise ValueError("study session must belong to the snapshot learner")
        if session.context_id not in context_ids:
            raise ValueError("study session must reference a snapshot context")
    for assessment in snapshot.assessments:
        if assessment.context_id not in context_ids:
            raise ValueError("assessment must reference a snapshot context")
    for plan in snapshot.study_plans:
        if plan.learner_id != learner_id:
            raise ValueError("study plan must belong to the snapshot learner")
        if plan.context_id is not None and plan.context_id not in context_ids:
            raise ValueError("study plan must reference a snapshot context")

    plan_ids = {plan.plan_id for plan in snapshot.study_plans}
    if len(plan_ids) != len(snapshot.study_plans):
        raise ValueError("snapshot cannot contain duplicate plan_id values")
    for task in snapshot.study_tasks:
        if task.plan_id not in plan_ids:
            raise ValueError("study task must reference a snapshot plan")
        if task.context_id not in context_ids:
            raise ValueError("study task must reference a snapshot context")
    return context_ids


def _validate_scoped_records(
    records,
    learner_id: UUID,
    context_ids: set[UUID],
    record_name: str,
) -> None:
    for record in records:
        if record.learner_id != learner_id:
            raise ValueError(f"{record_name} must belong to the snapshot learner")
        if record.context_id is not None and record.context_id not in context_ids:
            raise ValueError(f"{record_name} must reference a snapshot context")


def _kind_from_source(source: EvidenceSource) -> KnownFactKind:
    if source == EvidenceSource.ASSESSMENT_DERIVED:
        return KnownFactKind.DERIVED
    if source == EvidenceSource.COACH_INFERRED:
        return KnownFactKind.INFERRED
    return KnownFactKind.EXPLICIT
