"""Learner and LearningContext repository."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from educoach.persistence.datetime_utils import restore_utc

from educoach.models import (
    ContextStatus,
    ContextType,
    EducationStatus,
    Learner,
    LearningContext,
)
from educoach.persistence.tables import (
    LearnerRow,
    LearningContextRow,
)


class LearnerRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add_learner(self, learner: Learner) -> Learner:
        row = LearnerRow(
            learner_id=str(learner.learner_id),
            display_name=learner.display_name,
            education_status=learner.education_status.value,
            preferred_language=learner.preferred_language,
            timezone=learner.timezone,
            created_at=learner.created_at,
            updated_at=learner.updated_at,
        )

        self.session.add(row)
        self.session.flush()

        return learner

    def get_learner(
        self,
        learner_id: UUID,
    ) -> Learner | None:
        row = self.session.get(
            LearnerRow,
            str(learner_id),
        )

        if row is None:
            return None

        return Learner(
            learner_id=UUID(row.learner_id),
            display_name=row.display_name,
            education_status=EducationStatus(
                row.education_status
            ),
            preferred_language=row.preferred_language,
            timezone=row.timezone,
            created_at=restore_utc(row.created_at),
            updated_at=restore_utc(row.updated_at),
        )

    def add_context(
        self,
        context: LearningContext,
    ) -> LearningContext:
        row = LearningContextRow(
            context_id=str(context.context_id),
            learner_id=str(context.learner_id),
            context_type=context.context_type.value,
            program_code=context.program_code,
            grade_level=context.grade_level,
            track=context.track,
            exam_year=context.exam_year,
            status=context.status.value,
            started_at=context.started_at,
            ended_at=context.ended_at,
        )

        self.session.add(row)
        self.session.flush()

        return context

    def get_context(
        self,
        context_id: UUID,
    ) -> LearningContext | None:
        row = self.session.get(
            LearningContextRow,
            str(context_id),
        )

        if row is None:
            return None

        return self._context_from_row(row)

    def list_contexts(
        self,
        learner_id: UUID,
    ) -> list[LearningContext]:
        statement = (
            select(LearningContextRow)
            .where(
                LearningContextRow.learner_id
                == str(learner_id)
            )
            .order_by(
                LearningContextRow.program_code,
                LearningContextRow.context_id,
            )
        )

        rows = self.session.scalars(statement).all()

        return [
            self._context_from_row(row)
            for row in rows
        ]

    @staticmethod
    def _context_from_row(
        row: LearningContextRow,
    ) -> LearningContext:
        return LearningContext(
            context_id=UUID(row.context_id),
            learner_id=UUID(row.learner_id),
            context_type=ContextType(row.context_type),
            program_code=row.program_code,
            grade_level=row.grade_level,
            track=row.track,
            exam_year=row.exam_year,
            status=ContextStatus(row.status),
            started_at=row.started_at,
            ended_at=row.ended_at,
        )
