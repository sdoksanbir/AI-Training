"""Initial SQLAlchemy persistence tables."""

from datetime import date, datetime, time

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Float,
    Integer,
    String,
    Time,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class LearnerRow(Base):
    __tablename__ = "learners"

    learner_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
    )

    display_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    education_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    preferred_language: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
    )

    timezone: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )


class LearningContextRow(Base):
    __tablename__ = "learning_contexts"

    __table_args__ = (
        CheckConstraint(
            "grade_level IS NULL OR "
            "(grade_level >= 5 AND grade_level <= 12)",
            name="ck_learning_contexts_grade_level",
        ),
        CheckConstraint(
            "exam_year IS NULL OR "
            "(exam_year >= 2000 AND exam_year <= 2200)",
            name="ck_learning_contexts_exam_year",
        ),
        CheckConstraint(
            "ended_at IS NULL OR started_at IS NULL "
            "OR ended_at >= started_at",
            name="ck_learning_contexts_date_range",
        ),
    )

    context_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
    )

    learner_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey(
            "learners.learner_id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    context_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    program_code: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    grade_level: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    track: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    exam_year: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    started_at: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    ended_at: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )



class GoalRow(Base):
    __tablename__ = "goals"

    __table_args__ = (
        CheckConstraint(
            "(target_value IS NULL AND target_unit IS NULL) "
            "OR "
            "(target_value IS NOT NULL AND target_unit IS NOT NULL)",
            name="ck_goals_target_pair",
        ),
    )

    goal_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
    )

    learner_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey(
            "learners.learner_id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    context_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey(
            "learning_contexts.context_id",
            ondelete="CASCADE",
        ),
        nullable=True,
        index=True,
    )

    goal_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    description: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
    )

    target_value: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    target_unit: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    target_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    priority: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )


class AvailabilityRow(Base):
    __tablename__ = "availability"

    __table_args__ = (
        CheckConstraint(
            "day_of_week >= 0 AND day_of_week <= 6",
            name="ck_availability_day_of_week",
        ),
        CheckConstraint(
            "available_minutes IS NULL OR available_minutes >= 0",
            name="ck_availability_minutes",
        ),
        CheckConstraint(
            "(start_time IS NULL AND end_time IS NULL) "
            "OR "
            "(start_time IS NOT NULL AND end_time IS NOT NULL)",
            name="ck_availability_time_pair",
        ),
        CheckConstraint(
            "effective_until IS NULL OR effective_from IS NULL "
            "OR effective_until >= effective_from",
            name="ck_availability_effective_range",
        ),
    )

    availability_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
    )

    learner_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey(
            "learners.learner_id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    day_of_week: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    availability_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    available_minutes: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    start_time: Mapped[time | None] = mapped_column(
        Time,
        nullable=True,
    )

    end_time: Mapped[time | None] = mapped_column(
        Time,
        nullable=True,
    )

    effective_from: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    effective_until: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    source_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    notes: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )
