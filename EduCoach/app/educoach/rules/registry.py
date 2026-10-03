"""Minimal registry for implemented deterministic backend evaluators."""

from collections.abc import Callable
from dataclasses import dataclass

from .plan_budget import evaluate_plan_available_time_limit


class BackendRuleRegistryError(Exception):
    """Base error for backend rule registry failures."""


class DuplicateBackendRuleError(BackendRuleRegistryError):
    """Raised when the same backend rule id is registered twice."""


class BackendRuleNotFoundError(BackendRuleRegistryError):
    """Raised when an implemented backend rule cannot be found."""


@dataclass(frozen=True)
class BackendRuleDefinition:
    rule_id: str
    evaluator: Callable[..., object]

    def __post_init__(self) -> None:
        if not isinstance(self.rule_id, str) or not self.rule_id:
            raise ValueError("rule_id must be a non-empty string")
        if not callable(self.evaluator):
            raise ValueError("evaluator must be callable")


class BackendRuleRegistry:
    """Store only backend rules with active deterministic evaluators."""

    def __init__(self) -> None:
        self._definitions: dict[str, BackendRuleDefinition] = {}

    def register(self, definition: BackendRuleDefinition) -> None:
        if definition.rule_id in self._definitions:
            raise DuplicateBackendRuleError(
                f"Backend rule already registered: {definition.rule_id}"
            )
        self._definitions[definition.rule_id] = definition

    def get(self, rule_id: str) -> BackendRuleDefinition | None:
        return self._definitions.get(rule_id)

    def require(self, rule_id: str) -> BackendRuleDefinition:
        definition = self.get(rule_id)
        if definition is None:
            raise BackendRuleNotFoundError(
                f"Implemented backend rule not found: {rule_id}"
            )
        return definition

    def list_rules(self) -> tuple[BackendRuleDefinition, ...]:
        return tuple(self._definitions[key] for key in sorted(self._definitions))


def create_backend_rule_registry() -> BackendRuleRegistry:
    """Create the v0.1 registry of implemented backend evaluators."""

    registry = BackendRuleRegistry()
    registry.register(
        BackendRuleDefinition(
            rule_id="PLAN_AVAILABLE_TIME_LIMIT",
            evaluator=evaluate_plan_available_time_limit,
        )
    )
    return registry
