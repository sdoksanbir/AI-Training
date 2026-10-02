"""Initial SQLAlchemy persistence tables."""

from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
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
