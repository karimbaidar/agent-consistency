# Build State

## Current phase
Complete — all phased build prompt work shipped through Phase 5.

## Roadmap
- [x] Phase 0 — Foundation & context scaffolding
- [x] Phase 1 — Production-grade reliability core
- [x] Phase 2 — Framework-agnostic API + OpenTelemetry
- [x] Phase 3 — Microsoft Agent Framework adapter + instrument-your-own-agent
- [x] Phase 4 — False-success benchmark + leaderboard
- [x] Phase 5 — Positioning, docs & compliance framing

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
- Phase 5 completed README positioning around false-success bugs, the
  irreversible-action safety interlock, benchmark headline, production rollout
  guidance, compliance framing, and docs drift checks.
- Post-Phase 5 alignment added the supplied architecture image, a generated
  pending-refund receipt sample, and a diagram-to-receipt field map.

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
- The README uses the human-supplied architecture image at
  `assets/architecture.png`.
- The architecture image uses compact presentation labels; the source of truth
  remains the structured receipt JSON documented in `docs/diagram-receipt-map.md`.
- The pending-refund banner remains future collateral; do not add a generated
  banner image without human approval.

## Gotchas
- GitHub Pages deploy remains gated by `DEPLOY_GITHUB_PAGES` because the repo
  may not support Pages in every visibility/plan state.
- README benchmark numbers must stay synced with generated
  `benchmark/results.md`.
- `OtelReceiptExporter` is export-only; it intentionally returns an empty list
  because spans are not a receipt source of truth.
- Tamper evidence is hash-chain integrity, not signing or tamper-proof storage.
- The local sandbox can pick up an older editable install; use `PYTHONPATH=src`
  when validating this copied checkout directly.

## Next
- Maintain benchmark/docs sync on future changes.
- Future, not now: deeper native framework packages, hosted community
  leaderboard automation, signed receipts, richer graph visualization, and
  legal-review-specific compliance templates.

## Open questions for the human
- None.
