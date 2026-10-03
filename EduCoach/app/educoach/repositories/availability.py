"""Availability repository."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from educoach.models import (
    Availability,
    AvailabilityType,
    DayOfWeek,
    EvidenceSource,
)
from educoach.persistence.tables import AvailabilityRow


class AvailabilityRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(
        self,
        availability: Availability,
    ) -> Availability:
        row = AvailabilityRow(
            availability_id=str(
                availability.availability_id
            ),
            learner_id=str(availability.learner_id),
            day_of_week=int(availability.day_of_week),
            availability_type=(
                availability.availability_type.value
            ),
            available_minutes=(
                availability.available_minutes
            ),
            start_time=availability.start_time,
            end_time=availability.end_time,
            effective_from=availability.effective_from,
            effective_until=availability.effective_until,
            source_type=availability.source_type.value,
            notes=availability.notes,
        )

        self.session.add(row)
        self.session.flush()

        return availability

    def get(
        self,
        availability_id: UUID,
    ) -> Availability | None:
        row = self.session.get(
            AvailabilityRow,
            str(availability_id),
        )

        if row is None:
            return None

        return self._from_row(row)

    def list_for_learner(
        self,
        learner_id: UUID,
    ) -> list[Availability]:
        statement = (
            select(AvailabilityRow)
            .where(
                AvailabilityRow.learner_id
                == str(learner_id)
            )
            .order_by(
                AvailabilityRow.day_of_week,
                AvailabilityRow.start_time,
                AvailabilityRow.availability_id,
            )
        )

        rows = self.session.scalars(statement).all()

        return [
            self._from_row(row)
            for row in rows
        ]

    @staticmethod
    def _from_row(
        row: AvailabilityRow,
    ) -> Availability:
        return Availability(
            availability_id=UUID(
                row.availability_id
            ),
            learner_id=UUID(row.learner_id),
            day_of_week=DayOfWeek(
                row.day_of_week
            ),
            availability_type=AvailabilityType(
                row.availability_type
            ),
            available_minutes=row.available_minutes,
            start_time=row.start_time,
            end_time=row.end_time,
            effective_from=row.effective_from,
            effective_until=row.effective_until,
            source_type=EvidenceSource(
                row.source_type
            ),
            notes=row.notes,
        )
