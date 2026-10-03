from scripts.run_core_regression import run


def test_core_regression_suite_passes() -> None:
    results = run()
    assert results
    assert all(result.passed for result in results)
