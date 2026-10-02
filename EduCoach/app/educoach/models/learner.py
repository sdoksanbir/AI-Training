"""Core learner and learning-context domain models."""

from datetime import date, datetime, timezone
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class EducationStatus(StrEnum):
    MIDDLE_SCHOOL = "middle_school"
    HIGH_SCHOOL = "high_school"
    GRADUATE = "graduate"
    UNIVERSITY = "university"
    WORKING = "working"
    OTHER = "other"
    UNKNOWN = "unknown"


class ContextType(StrEnum):
    SCHOOL = "school"
    ENTRANCE_EXAM = "entrance_exam"
    PUBLIC_EXAM = "public_exam"
    ACADEMIC_EXAM = "academic_exam"
    LANGUAGE_EXAM = "language_exam"
    LANGUAGE_LEARNING = "language_learning"
    OTHER = "other"


class ContextStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    COMPLETED = "completed"


class EvidenceSource(StrEnum):
    LEARNER_REPORTED = "learner_reported"
    TEACHER_REPORTED = "teacher_reported"
    ASSESSMENT_DERIVED = "assessment_derived"
    COACH_INFERRED = "coach_inferred"
    SYSTEM_OBSERVED = "system_observed"


class Learner(BaseModel):
    model_config = ConfigDict(extra="forbid")

    learner_id: UUID = Field(default_factory=uuid4)
    display_name: str | None = None
    education_status: EducationStatus = EducationStatus.UNKNOWN
    preferred_language: str = "tr"
    timezone: str = "Europe/Istanbul"
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @field_validator("display_name")
    @classmethod
    def normalize_display_name(cls, value: str | None) -> str | None:
        if value is None:
            return None

        cleaned = value.strip()
        return cleaned or None


class LearningContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    context_id: UUID = Field(default_factory=uuid4)
    learner_id: UUID
    context_type: ContextType
    program_code: str = Field(min_length=1)
    grade_level: int | None = Field(default=None, ge=5, le=12)
    track: str | None = None
    exam_year: int | None = Field(default=None, ge=2000, le=2200)
    status: ContextStatus = ContextStatus.ACTIVE
    started_at: date | None = None
    ended_at: date | None = None

    @field_validator("program_code")
    @classmethod
    def normalize_program_code(cls, value: str) -> str:
        cleaned = value.strip()

        if not cleaned:
            raise ValueError("program_code boş olamaz")

        return cleaned

    @model_validator(mode="after")
    def validate_date_range(self) -> "LearningContext":
        if (
            self.started_at is not None
            and self.ended_at is not None
            and self.ended_at < self.started_at
        ):
            raise ValueError("ended_at, started_at tarihinden önce olamaz")

        return self
