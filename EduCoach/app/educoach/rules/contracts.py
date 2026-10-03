"""Immutable result contracts for deterministic backend rules."""

from dataclasses import dataclass
from enum import StrEnum


class RuleSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass(frozen=True)
class RuleViolation:
    rule_id: str
    severity: RuleSeverity
    message: str


@dataclass(frozen=True)
class RuleEvaluation:
    violations: tuple[RuleViolation, ...] = ()
