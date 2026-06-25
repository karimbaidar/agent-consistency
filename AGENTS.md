# AGENTS.md

## What This Is

`agent-consistency` is a reliability layer that catches **false-success bugs**:
cases where a tool call returns success but the business outcome did not happen.
Tool success is not business success. The package records evidence receipts,
checks state freshness, validates handoffs, verifies real-world outcomes, and
blocks unsafe continuation before an agent makes a customer-visible or
business-visible claim.

## Architecture Map

See `ARCHITECTURE.md` for the full design. The short version:

- `src/agent_consistency/run.py` owns `WorkflowRun` and `AgentStep`, the runtime
  surface that records state reads, handoffs, artifacts, outcomes, and issues.
- `src/agent_consistency/policy.py` resolves fail-open / fail-closed decisions
  from action criticality.
- `src/agent_consistency/outcome.py` defines deterministic outcome verifiers.
- `src/agent_consistency/store.py` defines receipt stores and exporters.
- `src/agent_consistency/api.py` exposes framework-agnostic decorator and
  context-manager helpers.
- `src/agent_consistency/adapters/` and `src/agent_consistency/integrations/`
  hold dependency-light framework wrappers.
- `benchmark/` contains deterministic false-success scenarios and harness code.

## Directory Layout

- Library code: `src/agent_consistency/`
- Tests: `tests/`
- Examples: `examples/`
- Benchmark: `benchmark/`
- Docs: `docs/`
- Repo-local reusable procedures: `skills/<name>/SKILL.md`
- CI and helper scripts: `.github/workflows/`, `scripts/`

## Commands

- Install dev deps: `python -m pip install -e ".[dev]"`
- Install docs deps: `python -m pip install -e ".[docs]"`
- Install optional OTel deps: `python -m pip install -e ".[otel]"`
- Install optional Postgres deps: `python -m pip install -e ".[postgres]"`
- Install optional Microsoft adapter deps: `python -m pip install -e ".[microsoft]"`
- Test: `python -m pytest`
- Lint: `ruff check src tests examples benchmark`
- Type check: `python -m mypy src/agent_consistency`
- Docs: `python -m mkdocs build --strict`
- Demo: `python examples/refund_false_success.py`
- Benchmark: `python -m benchmark.run --write-results benchmark/results.md`
- Commit hygiene: `scripts/check_commit_hygiene.sh origin/main..HEAD`

## Invariants

- Outcome verification checks **ground truth**, never a model judging itself.
- Side-effecting actions resolve an explicit **fail-open / fail-closed** policy;
  irreversible and financial actions default **fail-closed**.
- Contract checks are cheap and synchronous; receipt writes are buffered and can
  be flushed without making normal hot-path work depend on slow storage.
- The core library has no heavy required dependencies. Framework, backend, and
  OpenTelemetry integrations stay behind optional extras.
- Detect mode is honest: it reports risk from declared receipts and cannot infer
  claims or outcomes that were not recorded.

## Definition Of Done

- Requested behavior works.
- Tests and lint are green.
- Docs and README match the shipped code.
- `docs/STATE.md` records completed work, decisions, gotchas, and next action.
- No unrelated files are changed.
- Commit hygiene follows the build prompt's §2 rules: short human-style commit
  messages and no tool attribution.

