"""Current coaching-state domain model."""

from datetime import datetime, timezone
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CoachingStatus(StrEnum):
    ONBOARDING = "onboarding"
    ACTIVE = "active"
    REVIEW_NEEDED = "review_needed"
    PAUSED = "paused"


class CoachingState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state_id: UUID = Field(default_factory=uuid4)
    learner_id: UUID
    context_id: UUID | None = None

    status: CoachingStatus = CoachingStatus.ONBOARDING
    current_focus: str | None = None

    last_interaction_at: datetime | None = None
    next_review_at: datetime | None = None

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @field_validator("current_focus")
    @classmethod
    def normalize_current_focus(cls, value: str | None) -> str | None:
        if value is None:
            return None

        cleaned = value.strip()
        return cleaned or None
