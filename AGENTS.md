# AGENTS.md

## Project Structure

- Library code lives in `src/agent_consistency/`.
- Examples live in `examples/`.
- Tests live in `tests/`.

## Commands

- Install dev deps: `python -m pip install -e ".[dev]"`
- Test: `python -m pytest`
- Lint: `ruff check src tests examples`

## Rules

- Keep the library framework-agnostic.
- Do not claim to expose non-public model internals.
- Use user-facing terms like decision summary, checks performed, evidence used,
  handoff facts, contract checks, and outcome verification.
- Prefer small adapters and examples over heavy dependencies.
- Run tests before finalizing.
