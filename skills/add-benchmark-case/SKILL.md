# Skill: add-benchmark-case

## When to use

Use this when adding a deterministic false-success benchmark scenario.

## Steps

1. Add a case object in `benchmark/scenarios.py` with a unique name, category,
   and description.
2. Implement both modes: raw agent behavior and protected agent-consistency
   behavior.
3. Keep the case deterministic. Use local fakes and fixed state; no network or
   live provider calls.
4. Ensure the raw flow reports success while the protected flow catches the
   false-success condition.
5. Update expected totals in benchmark tests and regenerate
   `benchmark/results.md`.

## Conventions

- Categories use stable snake_case names.
- Cases should be small enough to understand in one screen.
- Scenario functions return structured results instead of printing.

## Definition of done

- `python -m benchmark.run --write-results benchmark/results.md` is stable.
- Tests assert the case contributes to the headline catch-rate number.
- README/docs use only generated benchmark numbers.

## Gotchas learned

- The benchmark proves declared scenarios, not all possible agent failures.

