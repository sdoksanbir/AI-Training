"""LearningEvidence repository."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from educoach.persistence.datetime_utils import restore_utc

from educoach.models import (
    EvidenceSource,
    EvidenceState,
    LearningEvidence,
)
from educoach.persistence.tables import LearningEvidenceRow


class LearningEvidenceRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(
        self,
        evidence: LearningEvidence,
    ) -> LearningEvidence:
        row = LearningEvidenceRow(
            evidence_id=str(evidence.evidence_id),
            learner_id=str(evidence.learner_id),
            context_id=str(evidence.context_id),
            area_type=evidence.area_type,
            area_code=evidence.area_code,
            state=evidence.state.value,
            source_type=evidence.source_type.value,
            confidence=evidence.confidence,
            assessment_id=(
                str(evidence.assessment_id)
                if evidence.assessment_id is not None
                else None
            ),
            observed_at=evidence.observed_at,
            valid_until=evidence.valid_until,
            notes=evidence.notes,
        )

        self.session.add(row)
        self.session.flush()

        return evidence

    def get(
        self,
        evidence_id: UUID,
    ) -> LearningEvidence | None:
        row = self.session.get(
            LearningEvidenceRow,
            str(evidence_id),
        )

        if row is None:
            return None

        return self._from_row(row)

    def list_for_learner(
        self,
        learner_id: UUID,
    ) -> list[LearningEvidence]:
        statement = (
            select(LearningEvidenceRow)
            .where(
                LearningEvidenceRow.learner_id
                == str(learner_id)
            )
            .order_by(LearningEvidenceRow.observed_at)
        )

        rows = self.session.scalars(statement).all()

        return [
            self._from_row(row)
            for row in rows
        ]

    @staticmethod
    def _from_row(
        row: LearningEvidenceRow,
    ) -> LearningEvidence:
        return LearningEvidence(
            evidence_id=UUID(row.evidence_id),
            learner_id=UUID(row.learner_id),
            context_id=UUID(row.context_id),
            area_type=row.area_type,
            area_code=row.area_code,
            state=EvidenceState(row.state),
            source_type=EvidenceSource(row.source_type),
            confidence=row.confidence,
            assessment_id=(
                UUID(row.assessment_id)
                if row.assessment_id is not None
                else None
            ),
            observed_at=restore_utc(row.observed_at),
            valid_until=restore_utc(row.valid_until),
            notes=row.notes,
        )
