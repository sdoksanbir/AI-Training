"""Typed contracts for response validation."""

from dataclasses import dataclass
from enum import StrEnum

from educoach.rules.contracts import RuleViolation


class ResponseValidationAction(StrEnum):
    PASS = "pass"
    AUTO_FIX = "auto_fix"
    REGENERATE = "regenerate"
    BLOCK = "block"


@dataclass(frozen=True)
class ResponseValidationReport:
    action: ResponseValidationAction
    violations: tuple[RuleViolation, ...] = ()
