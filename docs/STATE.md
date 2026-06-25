# Build State

## Current phase
Phase 5 — Positioning, docs & compliance framing

## Roadmap
- [x] Phase 0 — Foundation & context scaffolding
- [x] Phase 1 — Production-grade reliability core
- [x] Phase 2 — Framework-agnostic API + OpenTelemetry
- [x] Phase 3 — Microsoft Agent Framework adapter + instrument-your-own-agent
- [x] Phase 4 — False-success benchmark + leaderboard
- [ ] Phase 5 — Positioning, docs & compliance framing

## Done
- Existing baseline includes receipt recording, state freshness checks, handoff
  contracts, outcome checks, detect mode, tamper-evident receipt verification,
  lightweight LangGraph/CrewAI/AutoGen/Azure Durable-style adapters, docs, and
  examples.
- Phase 0 added canonical context files, repo-local skill playbooks, commit
  hygiene and secret guards, CI wiring, `.claude/settings.json`, and hardened
  ignore rules.
- Phase 1 added `FailurePolicy`, policy decisions on receipts, step
  criticality, idempotency-key duplicate prevention, `RefundSettlementVerifier`,
  `verify_outcome_with`, `BufferedReceiptStore`, `PostgresReceiptStore`,
  `OtelReceiptExporter`, receipt schema fields, and production docs.
- Phase 2 added framework-agnostic `reliability_gate(...)` and
  `verified_step(...)`, `GateDecision`, lazy optional OpenTelemetry span
  emission, fake-tracer tests, and API docs.
- Phase 3 added `MicrosoftAgentFrameworkConsistencyAdapter`, dependency-light
  wrapping for MAF-shaped agent methods and handoff records, deterministic fake
  MAF integration tests, and `examples/instrument_existing_agent/`.
- Phase 4 added six deterministic benchmark scenarios, a raw-vs-protected
  harness, generated `benchmark/results.md`, `LEADERBOARD.md`, benchmark docs,
  and tests. Generated headline: raw caught 0/6; agent-consistency caught 6/6.

## Decisions
- Keep the core dependency-free; optional integrations must live behind extras.
- Detect mode stays explicit about limits: it can report risk from declared
  receipts, not hidden or undeclared agent claims.
- Financial and irreversible steps force fail-closed even when a custom policy
  would otherwise allow fail-open; this protects side effects with no safe
  automatic compensation.
- Failed outcomes stay visible as failed receipts even when a low-criticality
  policy fail-opens and allows continuation.
- Microsoft Agent Framework support is currently an interface around
  MAF-shaped callables; it intentionally avoids importing Microsoft packages in
  the base install.
- Benchmark results are scenario-suite results only; they should not be framed
  as universal reliability guarantees.

## Gotchas
- GitHub Pages deploy remains gated by `DEPLOY_GITHUB_PAGES` because the repo
  may not support Pages in every visibility/plan state.
- README benchmark numbers must stay synced with generated
  `benchmark/results.md`.
- `OtelReceiptExporter` is export-only; it intentionally returns an empty list
  because spans are not a receipt source of truth.
- The local sandbox can pick up an older editable install; use `PYTHONPATH=src`
  when validating this copied checkout directly.

## Next
- Implement Phase 5 final positioning, docs drift check, and README polish.

## Open questions for the human
- None.
