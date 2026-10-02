"""Goal domain models."""

from datetime import date, datetime, timezone
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class GoalStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class GoalPriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Goal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    goal_id: UUID = Field(default_factory=uuid4)
    learner_id: UUID
    context_id: UUID | None = None

    goal_type: str = Field(min_length=1)
    description: str = Field(min_length=1)

    target_value: float | None = None
    target_unit: str | None = None
    target_date: date | None = None

    priority: GoalPriority = GoalPriority.MEDIUM
    status: GoalStatus = GoalStatus.ACTIVE

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @field_validator("goal_type", "description")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        cleaned = value.strip()

        if not cleaned:
            raise ValueError("alan boş olamaz")

        return cleaned

    @field_validator("target_unit")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None

        cleaned = value.strip()
        return cleaned or None
