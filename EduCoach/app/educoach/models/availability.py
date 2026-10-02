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
        if (self.start_time is None) != (self.end_time is None):
            raise ValueError(
                "start_time ve end_time birlikte verilmelidir"
            )

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

        has_time_range = (
            self.start_time is not None and self.end_time is not None
        )

        if (
            self.availability_type == AvailabilityType.AVAILABLE
            and self.available_minutes is None
            and not has_time_range
        ):
            raise ValueError(
                "AVAILABLE kaydı için available_minutes veya zaman aralığı gereklidir"
            )

        if (
            self.availability_type != AvailabilityType.AVAILABLE
            and self.available_minutes is not None
        ):
            raise ValueError(
                "available_minutes yalnız AVAILABLE kaydında kullanılabilir"
            )

        if has_time_range and self.available_minutes is not None:
            start_minutes = self.start_time.hour * 60 + self.start_time.minute
            end_minutes = self.end_time.hour * 60 + self.end_time.minute
            range_minutes = end_minutes - start_minutes

            if self.available_minutes != range_minutes:
                raise ValueError(
                    "available_minutes zaman aralığıyla tutarlı olmalıdır"
                )

        return self
