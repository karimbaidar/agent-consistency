from benchmark.run import render_markdown, run_benchmark
from benchmark.scenarios import BenchmarkCase, ScenarioResult


def test_benchmark_runs_end_to_end_with_deterministic_numbers():
    results, summary = run_benchmark()

    assert summary.total_cases == 6
    assert summary.raw_caught == 0
    assert summary.protected_caught == 6
    assert summary.by_category["outcome_verification"] == (4, 4)
    assert summary.by_category["state_freshness"] == (1, 1)
    assert summary.by_category["handoff_contract"] == (1, 1)
    assert all(result.raw.is_false_success for result in results)
    assert all(result.protected.caught_false_success for result in results)


def test_benchmark_markdown_contains_headline_and_reproduce_command(tmp_path):
    results, summary = run_benchmark()
    markdown = render_markdown(results)
    output = tmp_path / "results.md"

    output.write_text(markdown, encoding="utf-8")

    assert f"Headline: **{summary.headline}**." in markdown
    assert "python -m benchmark.run --write-results benchmark/results.md" in markdown
    assert output.read_text(encoding="utf-8") == markdown


def test_custom_case_can_be_added_via_same_schema():
    custom = BenchmarkCase(
        name="custom_false_success",
        category="custom",
        description="custom extension point",
        raw=lambda: ScenarioResult(
            reported_success=True,
            business_success=False,
            caught_false_success=False,
            reason="raw missed custom case",
        ),
        protected=lambda: ScenarioResult(
            reported_success=False,
            business_success=False,
            caught_false_success=True,
            reason="protected caught custom case",
            receipt_statuses=("failed",),
        ),
    )

    _, summary = run_benchmark([custom])

    assert summary.total_cases == 1
    assert summary.raw_caught == 0
    assert summary.protected_caught == 1
    assert summary.by_category["custom"] == (1, 1)

