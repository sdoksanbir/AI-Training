"""Assessment and assessment-result domain models."""

from datetime import date, datetime, timezone
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .learner import EvidenceSource


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Assessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assessment_id: UUID = Field(default_factory=uuid4)
    learner_id: UUID
    context_id: UUID

    assessment_type: str = Field(min_length=1)
    assessment_name: str = Field(min_length=1)
    assessment_date: date

    source_type: EvidenceSource = EvidenceSource.LEARNER_REPORTED
    notes: str | None = None

    created_at: datetime = Field(default_factory=utc_now)

    @field_validator("assessment_type", "assessment_name")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        cleaned = value.strip()

        if not cleaned:
            raise ValueError("alan boş olamaz")

        return cleaned


class AssessmentResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assessment_result_id: UUID = Field(default_factory=uuid4)
    assessment_id: UUID

    area_type: str | None = None
    area_code: str | None = None

    correct: int | None = Field(default=None, ge=0)
    incorrect: int | None = Field(default=None, ge=0)
    blank: int | None = Field(default=None, ge=0)

    net: float | None = None
    score: float | None = None
    percentage: float | None = Field(default=None, ge=0, le=100)
    grade: float | None = None
    duration_minutes: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_result(self) -> "AssessmentResult":
        metrics = (
            self.correct,
            self.incorrect,
            self.blank,
            self.net,
            self.score,
            self.percentage,
            self.grade,
            self.duration_minutes,
        )

        if all(value is None for value in metrics):
            raise ValueError("AssessmentResult en az bir ölçüm içermelidir")

        if (self.area_type is None) != (self.area_code is None):
            raise ValueError(
                "area_type ve area_code birlikte verilmelidir"
            )

        return self
