"""Learning-evidence domain models."""

from datetime import datetime, timezone
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .learner import EvidenceSource


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class EvidenceState(StrEnum):
    STRONG = "strong"
    ADEQUATE = "adequate"
    DEVELOPING = "developing"
    WEAK = "weak"
    UNKNOWN = "unknown"


class LearningEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_id: UUID = Field(default_factory=uuid4)
    learner_id: UUID
    context_id: UUID

    area_type: str = Field(min_length=1)
    area_code: str = Field(min_length=1)

    state: EvidenceState
    source_type: EvidenceSource

    confidence: float | None = Field(default=None, ge=0, le=1)
    assessment_id: UUID | None = None

    observed_at: datetime = Field(default_factory=utc_now)
    valid_until: datetime | None = None

    notes: str | None = None

    @field_validator("area_type", "area_code")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        cleaned = value.strip()

        if not cleaned:
            raise ValueError("alan boş olamaz")

        return cleaned

    @model_validator(mode="after")
    def validate_evidence(self) -> "LearningEvidence":
        if (
            self.source_type == EvidenceSource.ASSESSMENT_DERIVED
            and self.assessment_id is None
        ):
            raise ValueError(
                "assessment_derived evidence için assessment_id gereklidir"
            )

        if (
            self.valid_until is not None
            and self.valid_until < self.observed_at
        ):
            raise ValueError(
                "valid_until, observed_at değerinden önce olamaz"
            )

        return self
