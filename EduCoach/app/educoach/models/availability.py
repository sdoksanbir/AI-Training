"""Learner availability domain models."""

from datetime import date, time
from enum import IntEnum, StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .learner import EvidenceSource


class DayOfWeek(IntEnum):
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6


class AvailabilityType(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    FIXED_COMMITMENT = "fixed_commitment"


class Availability(BaseModel):
    model_config = ConfigDict(extra="forbid")

    availability_id: UUID = Field(default_factory=uuid4)
    learner_id: UUID

    day_of_week: DayOfWeek
    availability_type: AvailabilityType

    available_minutes: int | None = Field(default=None, ge=0)
    start_time: time | None = None
    end_time: time | None = None

    effective_from: date | None = None
    effective_until: date | None = None

    source_type: EvidenceSource = EvidenceSource.LEARNER_REPORTED
    notes: str | None = None

    @model_validator(mode="after")
    def validate_availability(self) -> "Availability":
        if (
            self.start_time is not None
            and self.end_time is not None
            and self.end_time <= self.start_time
        ):
            raise ValueError("end_time, start_time değerinden sonra olmalıdır")

        if (
            self.effective_from is not None
            and self.effective_until is not None
            and self.effective_until < self.effective_from
        ):
            raise ValueError(
                "effective_until, effective_from tarihinden önce olamaz"
            )

        if (
            self.availability_type == AvailabilityType.AVAILABLE
            and self.available_minutes is None
            and (self.start_time is None or self.end_time is None)
        ):
            raise ValueError(
                "AVAILABLE kaydı için available_minutes veya zaman aralığı gereklidir"
            )

        return self
