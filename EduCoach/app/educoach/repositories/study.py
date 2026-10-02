"""StudyPlan, StudyTask and StudySession repository."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from educoach.persistence.datetime_utils import restore_utc

from educoach.models import (
    PlanStatus,
    PlanType,
    StudyPlan,
    StudySession,
    StudyTask,
    TaskPriority,
    TaskStatus,
    TaskType,
)
from educoach.persistence.tables import (
    StudyPlanRow,
    StudySessionRow,
    StudyTaskRow,
)


class StudyRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add_plan(self, plan: StudyPlan) -> StudyPlan:
        row = StudyPlanRow(
            plan_id=str(plan.plan_id),
            learner_id=str(plan.learner_id),
            context_id=(
                str(plan.context_id)
                if plan.context_id is not None
                else None
            ),
            goal_id=(
                str(plan.goal_id)
                if plan.goal_id is not None
                else None
            ),
            title=plan.title,
            plan_type=plan.plan_type.value,
            start_date=plan.start_date,
            end_date=plan.end_date,
            status=plan.status.value,
            created_at=plan.created_at,
            updated_at=plan.updated_at,
        )

        self.session.add(row)
        self.session.flush()
        return plan

    def get_plan(
        self,
        plan_id: UUID,
    ) -> StudyPlan | None:
        row = self.session.get(
            StudyPlanRow,
            str(plan_id),
        )

        if row is None:
            return None

        return StudyPlan(
            plan_id=UUID(row.plan_id),
            learner_id=UUID(row.learner_id),
            context_id=(
                UUID(row.context_id)
                if row.context_id is not None
                else None
            ),
            goal_id=(
                UUID(row.goal_id)
                if row.goal_id is not None
                else None
            ),
            title=row.title,
            plan_type=PlanType(row.plan_type),
            start_date=row.start_date,
            end_date=row.end_date,
            status=PlanStatus(row.status),
            created_at=restore_utc(row.created_at),
            updated_at=restore_utc(row.updated_at),
        )

    def add_task(self, task: StudyTask) -> StudyTask:
        plan_row = self.session.get(
            StudyPlanRow,
            str(task.plan_id),
        )

        if plan_row is None:
            raise ValueError("StudyTask için StudyPlan bulunamadı")

        row = StudyTaskRow(
            task_id=str(task.task_id),
            plan_id=str(task.plan_id),
            learner_id=plan_row.learner_id,
            context_id=str(task.context_id),
            task_date=task.task_date,
            area_type=task.area_type,
            area_code=task.area_code,
            task_type=task.task_type.value,
            description=task.description,
            planned_minutes=task.planned_minutes,
            priority=task.priority.value,
            status=task.status.value,
            completed_at=task.completed_at,
        )

        self.session.add(row)
        self.session.flush()
        return task

    def get_task(
        self,
        task_id: UUID,
    ) -> StudyTask | None:
        row = self.session.get(
            StudyTaskRow,
            str(task_id),
        )

        if row is None:
            return None

        return self._task_from_row(row)

    def list_tasks(
        self,
        plan_id: UUID,
    ) -> list[StudyTask]:
        statement = (
            select(StudyTaskRow)
            .where(
                StudyTaskRow.plan_id == str(plan_id)
            )
            .order_by(
                StudyTaskRow.task_date,
                StudyTaskRow.task_id,
            )
        )

        rows = self.session.scalars(statement).all()

        return [
            self._task_from_row(row)
            for row in rows
        ]

    def add_session(
        self,
        study_session: StudySession,
    ) -> StudySession:
        row = StudySessionRow(
            session_id=str(study_session.session_id),
            learner_id=str(study_session.learner_id),
            context_id=str(study_session.context_id),
            task_id=(
                str(study_session.task_id)
                if study_session.task_id is not None
                else None
            ),
            started_at=study_session.started_at,
            ended_at=study_session.ended_at,
            duration_minutes=study_session.duration_minutes,
            area_type=study_session.area_type,
            area_code=study_session.area_code,
            completion_level=study_session.completion_level,
            learner_note=study_session.learner_note,
            created_at=study_session.created_at,
        )

        self.session.add(row)
        self.session.flush()
        return study_session

    def get_session(
        self,
        session_id: UUID,
    ) -> StudySession | None:
        row = self.session.get(
            StudySessionRow,
            str(session_id),
        )

        if row is None:
            return None

        return self._session_from_row(row)

    def list_sessions_for_task(
        self,
        task_id: UUID,
    ) -> list[StudySession]:
        statement = (
            select(StudySessionRow)
            .where(
                StudySessionRow.task_id == str(task_id)
            )
            .order_by(
                StudySessionRow.created_at,
                StudySessionRow.session_id,
            )
        )

        rows = self.session.scalars(statement).all()

        return [
            self._session_from_row(row)
            for row in rows
        ]

    @staticmethod
    def _task_from_row(row: StudyTaskRow) -> StudyTask:
        return StudyTask(
            task_id=UUID(row.task_id),
            plan_id=UUID(row.plan_id),
            context_id=UUID(row.context_id),
            task_date=row.task_date,
            area_type=row.area_type,
            area_code=row.area_code,
            task_type=TaskType(row.task_type),
            description=row.description,
            planned_minutes=row.planned_minutes,
            priority=TaskPriority(row.priority),
            status=TaskStatus(row.status),
            completed_at=restore_utc(row.completed_at),
        )

    @staticmethod
    def _session_from_row(
        row: StudySessionRow,
    ) -> StudySession:
        return StudySession(
            session_id=UUID(row.session_id),
            learner_id=UUID(row.learner_id),
            context_id=UUID(row.context_id),
            task_id=(
                UUID(row.task_id)
                if row.task_id is not None
                else None
            ),
            started_at=restore_utc(row.started_at),
            ended_at=restore_utc(row.ended_at),
            duration_minutes=row.duration_minutes,
            area_type=row.area_type,
            area_code=row.area_code,
            completion_level=row.completion_level,
            learner_note=row.learner_note,
            created_at=restore_utc(row.created_at),
        )
