"""Assessment and AssessmentResult repository."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from educoach.persistence.datetime_utils import restore_utc

from educoach.models import (
    Assessment,
    AssessmentResult,
    EvidenceSource,
)
from educoach.persistence.tables import (
    AssessmentResultRow,
    AssessmentRow,
)


class AssessmentRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add_assessment(
        self,
        assessment: Assessment,
    ) -> Assessment:
        row = AssessmentRow(
            assessment_id=str(assessment.assessment_id),
            learner_id=str(assessment.learner_id),
            context_id=str(assessment.context_id),
            assessment_type=assessment.assessment_type,
            assessment_name=assessment.assessment_name,
            assessment_date=assessment.assessment_date,
            source_type=assessment.source_type.value,
            notes=assessment.notes,
            created_at=assessment.created_at,
        )

        self.session.add(row)
        self.session.flush()

        return assessment

    def get_assessment(
        self,
        assessment_id: UUID,
    ) -> Assessment | None:
        row = self.session.get(
            AssessmentRow,
            str(assessment_id),
        )

        if row is None:
            return None

        return Assessment(
            assessment_id=UUID(row.assessment_id),
            learner_id=UUID(row.learner_id),
            context_id=UUID(row.context_id),
            assessment_type=row.assessment_type,
            assessment_name=row.assessment_name,
            assessment_date=row.assessment_date,
            source_type=EvidenceSource(row.source_type),
            notes=row.notes,
            created_at=restore_utc(row.created_at),
        )

    def list_for_learner(self, learner_id: UUID) -> list[Assessment]:
        statement = (
            select(AssessmentRow)
            .where(AssessmentRow.learner_id == str(learner_id))
            .order_by(
                AssessmentRow.assessment_date.desc(),
                AssessmentRow.assessment_id,
            )
        )
        return [
            self.get_assessment(UUID(row.assessment_id))
            for row in self.session.scalars(statement).all()
        ]

    def add_result(
        self,
        result: AssessmentResult,
    ) -> AssessmentResult:
        row = AssessmentResultRow(
            assessment_result_id=str(
                result.assessment_result_id
            ),
            assessment_id=str(result.assessment_id),
            area_type=result.area_type,
            area_code=result.area_code,
            correct=result.correct,
            incorrect=result.incorrect,
            blank=result.blank,
            net=result.net,
            score=result.score,
            percentage=result.percentage,
            grade=result.grade,
            duration_minutes=result.duration_minutes,
        )

        self.session.add(row)
        self.session.flush()

        return result

    def get_result(
        self,
        assessment_result_id: UUID,
    ) -> AssessmentResult | None:
        row = self.session.get(
            AssessmentResultRow,
            str(assessment_result_id),
        )

        if row is None:
            return None

        return self._result_from_row(row)

    def list_results(
        self,
        assessment_id: UUID,
    ) -> list[AssessmentResult]:
        statement = (
            select(AssessmentResultRow)
            .where(
                AssessmentResultRow.assessment_id
                == str(assessment_id)
            )
            .order_by(
                AssessmentResultRow.assessment_result_id
            )
        )

        rows = self.session.scalars(statement).all()

        return [
            self._result_from_row(row)
            for row in rows
        ]

    @staticmethod
    def _result_from_row(
        row: AssessmentResultRow,
    ) -> AssessmentResult:
        return AssessmentResult(
            assessment_result_id=UUID(
                row.assessment_result_id
            ),
            assessment_id=UUID(row.assessment_id),
            area_type=row.area_type,
            area_code=row.area_code,
            correct=row.correct,
            incorrect=row.incorrect,
            blank=row.blank,
            net=row.net,
            score=row.score,
            percentage=row.percentage,
            grade=row.grade,
            duration_minutes=row.duration_minutes,
        )
