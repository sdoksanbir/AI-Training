"""Study plan, task, and actual study-session domain models."""

from datetime import date, datetime, timezone
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class PlanType(StrEnum):
    DAILY = "daily"
    WEEKLY = "weekly"
    EXAM_PREPARATION = "exam_preparation"
    RECOVERY = "recovery"
    REVISION = "revision"
    CUSTOM = "custom"


class PlanStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TaskType(StrEnum):
    STUDY = "study"
    PRACTICE = "practice"
    REVISION = "revision"
    EXAM = "exam"
    READING = "reading"
    VOCABULARY = "vocabulary"
    HOMEWORK = "homework"
    ANALYSIS = "analysis"
    OTHER = "other"


class TaskStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class TaskPriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class StudyPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plan_id: UUID = Field(default_factory=uuid4)
    learner_id: UUID
    context_id: UUID | None = None
    goal_id: UUID | None = None

    title: str = Field(min_length=1)
    plan_type: PlanType

    start_date: date
    end_date: date

    status: PlanStatus = PlanStatus.DRAFT
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        cleaned = value.strip()

        if not cleaned:
            raise ValueError("title boş olamaz")

        return cleaned

    @model_validator(mode="after")
    def validate_date_range(self) -> "StudyPlan":
        if self.end_date < self.start_date:
            raise ValueError("end_date, start_date tarihinden önce olamaz")

        return self


class StudyTask(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: UUID = Field(default_factory=uuid4)
    plan_id: UUID
    context_id: UUID

    task_date: date

    area_type: str | None = None
    area_code: str | None = None

    task_type: TaskType
    description: str = Field(min_length=1)

    planned_minutes: int = Field(ge=1)
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.PENDING

    completed_at: datetime | None = None

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str) -> str:
        cleaned = value.strip()

        if not cleaned:
            raise ValueError("description boş olamaz")

        return cleaned

    @model_validator(mode="after")
    def validate_task(self) -> "StudyTask":
        if (self.area_type is None) != (self.area_code is None):
            raise ValueError(
                "area_type ve area_code birlikte verilmelidir"
            )

        if self.status == TaskStatus.COMPLETED and self.completed_at is None:
            raise ValueError(
                "COMPLETED görev için completed_at gereklidir"
            )

        if self.status != TaskStatus.COMPLETED and self.completed_at is not None:
            raise ValueError(
                "completed_at yalnız COMPLETED görevde kullanılabilir"
            )

        return self


class StudySession(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: UUID = Field(default_factory=uuid4)
    learner_id: UUID
    context_id: UUID
    task_id: UUID | None = None

    started_at: datetime | None = None
    ended_at: datetime | None = None

    duration_minutes: int = Field(ge=1)

    area_type: str | None = None
    area_code: str | None = None

    completion_level: float | None = Field(default=None, ge=0, le=1)
    learner_note: str | None = None

    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_session(self) -> "StudySession":
        if (self.started_at is None) != (self.ended_at is None):
            raise ValueError(
                "started_at ve ended_at birlikte verilmelidir"
            )

        if self.started_at is not None and self.ended_at is not None:
            if self.ended_at <= self.started_at:
                raise ValueError(
                    "ended_at, started_at değerinden sonra olmalıdır"
                )

            elapsed_seconds = (
                self.ended_at - self.started_at
            ).total_seconds()

            if elapsed_seconds != self.duration_minutes * 60:
                raise ValueError(
                    "duration_minutes başlangıç ve bitiş zamanıyla "
                    "tutarlı olmalıdır"
                )

        if (self.area_type is None) != (self.area_code is None):
            raise ValueError(
                "area_type ve area_code birlikte verilmelidir"
            )

        return self
