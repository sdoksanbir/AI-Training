"""Preference repository."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from educoach.persistence.datetime_utils import restore_utc

from educoach.models import (
    EvidenceSource,
    Preference,
)
from educoach.persistence.tables import PreferenceRow


class PreferenceRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(
        self,
        preference: Preference,
    ) -> Preference:
        row = PreferenceRow(
            preference_id=str(
                preference.preference_id
            ),
            learner_id=str(preference.learner_id),
            context_id=(
                str(preference.context_id)
                if preference.context_id is not None
                else None
            ),
            preference_key=preference.preference_key,
            preference_value=preference.preference_value,
            source_type=preference.source_type.value,
            confidence=preference.confidence,
            created_at=preference.created_at,
            updated_at=preference.updated_at,
        )

        self.session.add(row)
        self.session.flush()

        return preference

    def get(
        self,
        preference_id: UUID,
    ) -> Preference | None:
        row = self.session.get(
            PreferenceRow,
            str(preference_id),
        )

        if row is None:
            return None

        return self._from_row(row)

    def list_for_learner(
        self,
        learner_id: UUID,
    ) -> list[Preference]:
        statement = (
            select(PreferenceRow)
            .where(
                PreferenceRow.learner_id
                == str(learner_id)
            )
            .order_by(
                PreferenceRow.preference_key,
                PreferenceRow.preference_id,
            )
        )

        rows = self.session.scalars(statement).all()

        return [
            self._from_row(row)
            for row in rows
        ]

    @staticmethod
    def _from_row(
        row: PreferenceRow,
    ) -> Preference:
        return Preference(
            preference_id=UUID(row.preference_id),
            learner_id=UUID(row.learner_id),
            context_id=(
                UUID(row.context_id)
                if row.context_id is not None
                else None
            ),
            preference_key=row.preference_key,
            preference_value=row.preference_value,
            source_type=EvidenceSource(
                row.source_type
            ),
            confidence=row.confidence,
            created_at=restore_utc(row.created_at),
            updated_at=restore_utc(row.updated_at),
        )
