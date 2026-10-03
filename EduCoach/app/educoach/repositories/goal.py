"""Goal repository."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from educoach.persistence.datetime_utils import restore_utc

from educoach.models import (
    Goal,
    GoalPriority,
    GoalStatus,
)
from educoach.persistence.tables import GoalRow


class GoalRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, goal: Goal) -> Goal:
        row = GoalRow(
            goal_id=str(goal.goal_id),
            learner_id=str(goal.learner_id),
            context_id=(
                str(goal.context_id)
                if goal.context_id is not None
                else None
            ),
            goal_type=goal.goal_type,
            description=goal.description,
            target_value=goal.target_value,
            target_unit=goal.target_unit,
            target_date=goal.target_date,
            priority=goal.priority.value,
            status=goal.status.value,
            created_at=goal.created_at,
            updated_at=goal.updated_at,
        )

        self.session.add(row)
        self.session.flush()

        return goal

    def get(self, goal_id: UUID) -> Goal | None:
        row = self.session.get(
            GoalRow,
            str(goal_id),
        )

        if row is None:
            return None

        return self._from_row(row)

    def list_for_learner(
        self,
        learner_id: UUID,
    ) -> list[Goal]:
        statement = (
            select(GoalRow)
            .where(
                GoalRow.learner_id == str(learner_id)
            )
            .order_by(GoalRow.created_at, GoalRow.goal_id)
        )

        rows = self.session.scalars(statement).all()

        return [
            self._from_row(row)
            for row in rows
        ]

    @staticmethod
    def _from_row(row: GoalRow) -> Goal:
        return Goal(
            goal_id=UUID(row.goal_id),
            learner_id=UUID(row.learner_id),
            context_id=(
                UUID(row.context_id)
                if row.context_id is not None
                else None
            ),
            goal_type=row.goal_type,
            description=row.description,
            target_value=row.target_value,
            target_unit=row.target_unit,
            target_date=row.target_date,
            priority=GoalPriority(row.priority),
            status=GoalStatus(row.status),
            created_at=restore_utc(row.created_at),
            updated_at=restore_utc(row.updated_at),
        )
