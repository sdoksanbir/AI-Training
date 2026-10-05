from scripts.run_core_regression import run


def test_core_regression_suite_passes() -> None:
    results = run()
    assert [result.name for result in results] == [
        "response_generated",
        "learner_context_present",
        "program_filter_applied",
        "repetition_loop_auto_fixed",
        "numeric_claim_regenerated",
        "regeneration_budget_bounded",
        "ambiguous_context_stops_generation",
        "learner_memory_isolated",
    ]
    assert all(result.passed for result in results)
