from dataclasses import FrozenInstanceError

import pytest

from educoach.rules import (
    BackendRuleDefinition,
    BackendRuleNotFoundError,
    BackendRuleRegistry,
    DuplicateBackendRuleError,
    create_backend_rule_registry,
    evaluate_plan_available_time_limit,
)


def test_builtin_registry_contains_only_implemented_backend_rule() -> None:
    registry = create_backend_rule_registry()

    assert tuple(rule.rule_id for rule in registry.list_rules()) == (
        "PLAN_AVAILABLE_TIME_LIMIT",
    )


def test_plan_rule_points_to_active_evaluator() -> None:
    definition = create_backend_rule_registry().require(
        "PLAN_AVAILABLE_TIME_LIMIT"
    )

    assert definition.evaluator is evaluate_plan_available_time_limit


@pytest.mark.parametrize(
    "deferred_rule_id",
    [
        "PLAN_TIME_OVERLAP",
        "ASSESSMENT_UNKNOWN_RESULT",
        "YKS_NET_SCORE_CONFUSION",
        "OUTPUT_REPETITION_LOOP",
    ],
)
def test_deferred_or_non_backend_rules_are_not_registered(
    deferred_rule_id: str,
) -> None:
    assert create_backend_rule_registry().get(deferred_rule_id) is None


def test_duplicate_rule_id_is_rejected() -> None:
    registry = BackendRuleRegistry()
    definition = BackendRuleDefinition("EXAMPLE", lambda: None)
    registry.register(definition)

    with pytest.raises(DuplicateBackendRuleError):
        registry.register(BackendRuleDefinition("EXAMPLE", lambda: None))


def test_missing_implemented_rule_raises() -> None:
    with pytest.raises(BackendRuleNotFoundError):
        BackendRuleRegistry().require("MISSING")


def test_custom_rule_listing_is_deterministic() -> None:
    registry = BackendRuleRegistry()
    registry.register(BackendRuleDefinition("SECOND", lambda: None))
    registry.register(BackendRuleDefinition("FIRST", lambda: None))

    assert tuple(rule.rule_id for rule in registry.list_rules()) == (
        "FIRST",
        "SECOND",
    )


def test_rule_definition_is_immutable_and_keeps_string_id() -> None:
    definition = BackendRuleDefinition("EXAMPLE", lambda: None)

    assert definition.rule_id == "EXAMPLE"
    with pytest.raises(FrozenInstanceError):
        definition.rule_id = "CHANGED"
