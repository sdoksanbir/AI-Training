"""Learner preference domain models."""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .learner import EvidenceSource


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


PreferenceValue = str | int | float | bool


class Preference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    preference_id: UUID = Field(default_factory=uuid4)
    learner_id: UUID
    context_id: UUID | None = None

    preference_key: str = Field(min_length=1)
    preference_value: PreferenceValue

    source_type: EvidenceSource = EvidenceSource.LEARNER_REPORTED
    confidence: float | None = Field(default=None, ge=0, le=1)

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @field_validator("preference_key")
    @classmethod
    def normalize_preference_key(cls, value: str) -> str:
        cleaned = value.strip()

        if not cleaned:
            raise ValueError("preference_key boş olamaz")

        return cleaned
