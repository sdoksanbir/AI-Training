"""Learner Memory application service."""

from collections.abc import Iterable
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session, sessionmaker

from educoach.models import (
    Assessment,
    AssessmentResult,
    EvidenceSource,
    Learner,
    LearningContext,
    LearningEvidence,
    StudyPlan,
    StudySession,
    StudyTask,
    TaskStatus,
)
from educoach.repositories import (
    AssessmentRepository,
    AvailabilityRepository,
    CoachingStateRepository,
    GoalRepository,
    LearnerRepository,
    LearningEvidenceRepository,
    PreferenceRepository,
    StudyRepository,
)

from .snapshot import LearnerMemorySnapshot


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

    def save_study_plan(
        self,
        plan: StudyPlan,
        tasks: Iterable[StudyTask] = (),
    ) -> StudyPlan:
        task_items = tuple(tasks)

        for task in task_items:
            if task.plan_id != plan.plan_id:
                raise ValueError(
                    "StudyTask plan_id, kayıt edilen StudyPlan "
                    "ile aynı olmalıdır"
                )

            if not (
                plan.start_date
                <= task.task_date
                <= plan.end_date
            ):
                raise ValueError(
                    "StudyTask task_date, StudyPlan tarih "
                    "aralığında olmalıdır"
                )

            if (
                plan.context_id is not None
                and task.context_id != plan.context_id
            ):
                raise ValueError(
                    "Context'e özel StudyPlan içindeki "
                    "StudyTask aynı context'e ait olmalıdır"
                )

        with self.session_factory() as session:
            repository = StudyRepository(session)
            goal_repository = GoalRepository(session)

            with session.begin():
                if (
                    plan.goal_id is not None
                    and plan.context_id is not None
                ):
                    goal = goal_repository.get(plan.goal_id)

                    if (
                        goal is not None
                        and goal.context_id is not None
                        and goal.context_id != plan.context_id
                    ):
                        raise ValueError(
                            "Context'e özel StudyPlan, başka bir "
                            "context'e ait Goal kullanamaz"
                        )

                repository.add_plan(plan)

                for task in task_items:
                    repository.add_task(task)

        return plan

    def record_study_session(
        self,
        study_session: StudySession,
    ) -> StudySession:
        """Kaydedilmiş bir çalışma oturumunu öğrenci hafızasına ekler."""

        with self.session_factory() as session:
            repository = StudyRepository(session)

            with session.begin():
                if study_session.task_id is not None:
                    task = repository.get_task(study_session.task_id)

                    if task is None:
                        raise ValueError(
                            "StudySession için StudyTask bulunamadı"
                        )

                    plan = repository.get_plan(task.plan_id)

                    if plan is None or plan.learner_id != study_session.learner_id:
                        raise ValueError(
                            "StudySession learner_id, görevin öğrencisiyle "
                            "aynı olmalıdır"
                        )

                    if task.context_id != study_session.context_id:
                        raise ValueError(
                            "StudySession context_id, görevin context'iyle "
                            "aynı olmalıdır"
                        )

                    if (
                        study_session.completion_level is not None
                        and study_session.completion_level >= 1
                    ):
                        task.status = TaskStatus.COMPLETED
                        task.completed_at = datetime.now(timezone.utc)
                    else:
                        task.status = TaskStatus.IN_PROGRESS
                        task.completed_at = None

                    repository.update_task(task)

                repository.add_session(study_session)

        return study_session

    def get_learner_memory_snapshot(
        self,
        learner_id: UUID,
    ) -> LearnerMemorySnapshot:
        """Persist edilmiş Learner Memory verisini tek read modelde toplar."""
        with self.session_factory() as session:
            learner_repository = LearnerRepository(session)
            learner = learner_repository.get_learner(learner_id)

            if learner is None:
                raise ValueError("Learner bulunamadı")

            assessment_repository = AssessmentRepository(session)
            study_repository = StudyRepository(session)
            assessments = assessment_repository.list_for_learner(learner_id)
            results = tuple(
                result
                for assessment in assessments
                for result in assessment_repository.list_results(
                    assessment.assessment_id
                )
            )

            return LearnerMemorySnapshot(
                learner=learner,
                contexts=tuple(learner_repository.list_contexts(learner_id)),
                goals=tuple(GoalRepository(session).list_for_learner(learner_id)),
                availability=tuple(
                    AvailabilityRepository(session).list_for_learner(learner_id)
                ),
                assessments=tuple(assessments),
                assessment_results=results,
                learning_evidence=tuple(
                    LearningEvidenceRepository(session).list_for_learner(learner_id)
                ),
                study_plans=tuple(study_repository.list_plans_for_learner(learner_id)),
                study_tasks=tuple(study_repository.list_tasks_for_learner(learner_id)),
                study_sessions=tuple(
                    study_repository.list_sessions_for_learner(learner_id)
                ),
                preferences=tuple(
                    PreferenceRepository(session).list_for_learner(learner_id)
                ),
                coaching_states=tuple(
                    CoachingStateRepository(session).list_for_learner(learner_id)
                ),
            )
