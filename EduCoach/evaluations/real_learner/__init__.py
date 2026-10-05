"""Evaluation-only real learner intake, validation, and split contracts."""

from .contracts import (
    CaseFileValidationError,
    RealLearnerEvaluationCase,
    SanitizedFact,
    load_validated_cases,
    scan_case_for_likely_identifiers,
)
from .splitting import (
    SPLIT_POLICY_VERSION,
    SplitManifest,
    split_cases,
    write_split,
)

__all__ = [
    "CaseFileValidationError",
    "RealLearnerEvaluationCase",
    "SPLIT_POLICY_VERSION",
    "SanitizedFact",
    "SplitManifest",
    "load_validated_cases",
    "scan_case_for_likely_identifiers",
    "split_cases",
    "write_split",
]
