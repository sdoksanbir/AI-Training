"""Initial SQLAlchemy persistence tables."""

from datetime import date, datetime, time

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Float,
    Integer,
    String,
    Time,
    UniqueConstraint,
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
        UniqueConstraint(
            "context_id",
            "learner_id",
            name="uq_learning_contexts_context_learner",
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
        ForeignKeyConstraint(
            ["context_id", "learner_id"],
            [
                "learning_contexts.context_id",
                "learning_contexts.learner_id",
            ],
            name="fk_goals_context_owner",
            ondelete="CASCADE",
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



class AssessmentRow(Base):
    __tablename__ = "assessments"

    __table_args__ = (
        ForeignKeyConstraint(
            ["context_id", "learner_id"],
            [
                "learning_contexts.context_id",
                "learning_contexts.learner_id",
            ],
            name="fk_assessments_context_owner",
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "assessment_id",
            "learner_id",
            "context_id",
            name="uq_assessments_assessment_learner_context",
        ),
    )

    assessment_id: Mapped[str] = mapped_column(
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

    context_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )

    assessment_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    assessment_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    assessment_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    source_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    notes: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )


class AssessmentResultRow(Base):
    __tablename__ = "assessment_results"

    __table_args__ = (
        CheckConstraint(
            "(area_type IS NULL AND area_code IS NULL) "
            "OR "
            "(area_type IS NOT NULL AND area_code IS NOT NULL)",
            name="ck_assessment_results_area_pair",
        ),
        CheckConstraint(
            "correct IS NULL OR correct >= 0",
            name="ck_assessment_results_correct",
        ),
        CheckConstraint(
            "incorrect IS NULL OR incorrect >= 0",
            name="ck_assessment_results_incorrect",
        ),
        CheckConstraint(
            "blank IS NULL OR blank >= 0",
            name="ck_assessment_results_blank",
        ),
        CheckConstraint(
            "percentage IS NULL OR "
            "(percentage >= 0 AND percentage <= 100)",
            name="ck_assessment_results_percentage",
        ),
        CheckConstraint(
            "duration_minutes IS NULL OR duration_minutes >= 0",
            name="ck_assessment_results_duration",
        ),
        CheckConstraint(
            "correct IS NOT NULL OR "
            "incorrect IS NOT NULL OR "
            "blank IS NOT NULL OR "
            "net IS NOT NULL OR "
            "score IS NOT NULL OR "
            "percentage IS NOT NULL OR "
            "grade IS NOT NULL OR "
            "duration_minutes IS NOT NULL",
            name="ck_assessment_results_has_metric",
        ),
    )

    assessment_result_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
    )

    assessment_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey(
            "assessments.assessment_id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    area_type: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    area_code: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    correct: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    incorrect: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    blank: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    net: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    percentage: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    grade: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    duration_minutes: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )


class LearningEvidenceRow(Base):
    __tablename__ = "learning_evidence"

    __table_args__ = (
        CheckConstraint(
            "confidence IS NULL OR "
            "(confidence >= 0 AND confidence <= 1)",
            name="ck_learning_evidence_confidence",
        ),
        CheckConstraint(
            "valid_until IS NULL OR valid_until >= observed_at",
            name="ck_learning_evidence_validity",
        ),
        CheckConstraint(
            "source_type != 'assessment_derived' "
            "OR assessment_id IS NOT NULL",
            name="ck_learning_evidence_assessment_source",
        ),
        ForeignKeyConstraint(
            ["context_id", "learner_id"],
            [
                "learning_contexts.context_id",
                "learning_contexts.learner_id",
            ],
            name="fk_learning_evidence_context_owner",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            [
                "assessment_id",
                "learner_id",
                "context_id",
            ],
            [
                "assessments.assessment_id",
                "assessments.learner_id",
                "assessments.context_id",
            ],
            name="fk_learning_evidence_assessment_owner",
            ondelete="CASCADE",
        ),
    )

    evidence_id: Mapped[str] = mapped_column(
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

    context_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )

    area_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    area_code: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    state: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    source_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    confidence: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    assessment_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
        index=True,
    )

    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    valid_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    notes: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )
