"""Immutable contracts for validated Learner Memory write-back."""

from dataclasses import dataclass
from enum import StrEnum

from educoach.models import StudyPlan, StudyTask
from educoach.rules.contracts import RuleViolation


class WriteValidationStatus(StrEnum):
    VALID = "valid"
    REJECTED = "rejected"
    INCONCLUSIVE = "inconclusive"


@dataclass(frozen=True)
class StudyPlanWriteProposal:
    plan: StudyPlan
    tasks: tuple[StudyTask, ...]


@dataclass(frozen=True)
class StudyPlanWriteValidationReport:
    status: WriteValidationStatus
    violations: tuple[RuleViolation, ...] = ()
