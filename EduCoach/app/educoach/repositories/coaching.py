"""CoachingState repository."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from educoach.models import (
    CoachingState,
    CoachingStatus,
)
from educoach.persistence.tables import CoachingStateRow


def _restore_utc(
    value: datetime | None,
) -> datetime | None:
    if value is None:
        return None

    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value


class CoachingStateRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(
        self,
        state: CoachingState,
    ) -> CoachingState:
        row = CoachingStateRow(
            state_id=str(state.state_id),
            learner_id=str(state.learner_id),
            context_id=(
                str(state.context_id)
                if state.context_id is not None
                else None
            ),
            status=state.status.value,
            current_focus=state.current_focus,
            last_interaction_at=state.last_interaction_at,
            next_review_at=state.next_review_at,
            created_at=state.created_at,
            updated_at=state.updated_at,
        )

        self.session.add(row)
        self.session.flush()

        return state

    def get(
        self,
        state_id: UUID,
    ) -> CoachingState | None:
        row = self.session.get(
            CoachingStateRow,
            str(state_id),
        )

        if row is None:
            return None

        return self._from_row(row)

    def list_for_learner(
        self,
        learner_id: UUID,
    ) -> list[CoachingState]:
        statement = (
            select(CoachingStateRow)
            .where(
                CoachingStateRow.learner_id
                == str(learner_id)
            )
            .order_by(CoachingStateRow.created_at)
        )

        rows = self.session.scalars(statement).all()

        return [
            self._from_row(row)
            for row in rows
        ]

    @staticmethod
    def _from_row(
        row: CoachingStateRow,
    ) -> CoachingState:
        return CoachingState(
            state_id=UUID(row.state_id),
            learner_id=UUID(row.learner_id),
            context_id=(
                UUID(row.context_id)
                if row.context_id is not None
                else None
            ),
            status=CoachingStatus(row.status),
            current_focus=row.current_focus,
            last_interaction_at=_restore_utc(
                row.last_interaction_at
            ),
            next_review_at=_restore_utc(
                row.next_review_at
            ),
            created_at=_restore_utc(row.created_at),
            updated_at=_restore_utc(row.updated_at),
        )
