import argparse
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

from .scenarios import BenchmarkCase, BenchmarkCaseResult, categories, run_cases


@dataclass(frozen=True)
class BenchmarkSummary:
    total_cases: int
    raw_caught: int
    protected_caught: int
    by_category: dict[str, tuple[int, int]]

    @property
    def headline(self) -> str:
        return (
            f"raw caught {self.raw_caught}/{self.total_cases}; "
            f"agent-consistency caught {self.protected_caught}/{self.total_cases}"
        )


def summarize(results: Sequence[BenchmarkCaseResult]) -> BenchmarkSummary:
    category_totals = Counter(result.case.category for result in results)
    category_caught = Counter(
        result.case.category for result in results if result.protected.caught_false_success
    )
    return BenchmarkSummary(
        total_cases=len(results),
        raw_caught=sum(1 for result in results if result.raw.caught_false_success),
        protected_caught=sum(1 for result in results if result.protected.caught_false_success),
        by_category={
            category: (category_caught[category], category_totals[category])
            for category in categories(results)
        },
    )


def render_markdown(results: Sequence[BenchmarkCaseResult]) -> str:
    summary = summarize(results)
    lines = [
        "# False-Success Benchmark Results",
        "",
        f"Headline: **{summary.headline}**.",
        "",
        "These numbers describe the deterministic scenarios in this repository. "
        "They are not a universal claim about every possible agent workflow.",
        "",
        "## Cases",
        "",
        "| Case | Category | Raw caught? | agent-consistency caught? | Protected receipt status |",
        "| --- | --- | --- | --- | --- |",
    ]
    for result in results:
        raw = "yes" if result.raw.caught_false_success else "no"
        protected = "yes" if result.protected.caught_false_success else "no"
        statuses = ", ".join(result.protected.receipt_statuses) or "none"
        lines.append(
            f"| `{result.case.name}` | `{result.case.category}` | {raw} | "
            f"{protected} | {statuses} |"
        )
    lines.extend(
        [
            "",
            "## Category Catch Rate",
            "",
            "| Category | agent-consistency caught |",
            "| --- | --- |",
        ]
    )
    for category, (caught, total) in summary.by_category.items():
        lines.append(f"| `{category}` | {caught}/{total} |")
    lines.extend(
        [
            "",
            "## Reproduce",
            "",
            "```bash",
            "python -m benchmark.run --write-results benchmark/results.md",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def run_benchmark(
    cases: Optional[Sequence[BenchmarkCase]] = None,
) -> tuple[list[BenchmarkCaseResult], BenchmarkSummary]:
    results = run_cases(cases)
    return results, summarize(results)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run deterministic false-success benchmark")
    parser.add_argument("--write-results", help="write Markdown results to this path")
    args = parser.parse_args(argv)

    results, summary = run_benchmark()
    markdown = render_markdown(results)
    if args.write_results:
        path = Path(args.write_results)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(markdown, encoding="utf-8")
    else:
        print(markdown)
    print(summary.headline)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
