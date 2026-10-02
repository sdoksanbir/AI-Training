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
    StudyPlan,
    StudyTask,
)
from educoach.repositories import (
    AssessmentRepository,
    GoalRepository,
    LearnerRepository,
    LearningEvidenceRepository,
    StudyRepository,
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
