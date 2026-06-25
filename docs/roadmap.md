# Roadmap

The phased build prompt is complete through Phase 6. This page records what is
shipped now and what remains future work, not a dated release promise.

## Completed Phases

- Phase 0: project context scaffolding, repo-local skills, Claude settings,
  commit hygiene, secret checks, and CI wiring.
- Phase 1: fail-open/fail-closed policy decisions, step criticality,
  idempotency keys, outcome verifiers, buffered receipts, Postgres storage, and
  OpenTelemetry export support.
- Phase 2: framework-agnostic `reliability_gate(...)`, `verified_step(...)`,
  `GateDecision`, optional OTel span emission, and public API docs.
- Phase 3: dependency-light Microsoft Agent Framework-shaped adapter plus the
  instrument-your-own-agent example path.
- Phase 4: deterministic false-success benchmark, generated results, and
  leaderboard submission format.
- Phase 5: launch positioning, README benchmark framing, production notes,
  compliance framing, and docs drift cleanup.
- Phase 6: native Microsoft Agent Framework integration surface for async
  `Agent.run(...)`, middleware, function/tool middleware, and streaming methods.

## Future, Not Now

- Deeper native framework packages that depend on real LangGraph, CrewAI,
  AutoGen, Azure Durable, or OpenAI Agents SDK runtimes.
- Hosted community leaderboard automation and submission validation.
- Signed receipts behind an optional crypto extra.
- Richer graph visualization for receipt chains and handoffs.
- Legal-review-specific compliance templates maintained with counsel.

Benchmark results remain scenario-suite results only. They should stay synced
with `benchmark/results.md` and should not be described as universal reliability
guarantees.
