# Build State

## Current phase
Complete — phased build prompt work shipped through Phase 6.

## Roadmap
- [x] Phase 0 — Foundation & context scaffolding
- [x] Phase 1 — Production-grade reliability core
- [x] Phase 2 — Framework-agnostic API + OpenTelemetry
- [x] Phase 3 — Microsoft Agent Framework adapter + instrument-your-own-agent
- [x] Phase 4 — False-success benchmark + leaderboard
- [x] Phase 5 — Positioning, docs & compliance framing
- [x] Phase 6 — Native Microsoft Agent Framework integration

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
  pending-refund receipt sample, and a diagram-to-receipt field map. The current
  image/map use the `fresh`, `tool_call`, `tool_response`, `outcome_verify`, and
  `decision_blocked` label set.
- Phase 6 fixed CI pytest import path drift for the top-level `benchmark/`
  package and added `MicrosoftAgentFrameworkNativeIntegration` for async
  `Agent.run(...)`, async agent middleware, function/tool middleware, streaming
  methods, context metadata mapping, and extra-gated Microsoft dependency
  wiring.
- The live Microsoft Agent Framework hardening lane added
  `tests/integration/test_microsoft_agent_framework_live.py` and a CI
  `microsoft-live` job. That job installs `agent-consistency[test,microsoft]`
  on Python 3.11, constructs a real `agent_framework.Agent` with a deterministic
  local `BaseChatClient`, and verifies both allow and fail-closed outcomes
  without external provider credentials.
- Phase F added the static false-success scanner and repo report card:
  `agent-consistency scan`, JSON/Markdown output, public GitHub URL scanning by
  temporary clone, baselines, suppression comments, and a `false-success scan`
  GitHub Action.
- The interactive False Success Lab UI now lives in the separate
  `false-success-lab` repo. This package repo keeps only scanner
  APIs, report schemas, receipt/runtime code, and docs links.

## Decisions
- Keep the core dependency-free; optional integrations must live behind extras.
- Detect mode stays explicit about limits: it can report risk from declared
  receipts, not hidden or undeclared agent claims.
- Financial and irreversible steps force fail-closed even when a custom policy
  would otherwise allow fail-open; this protects side effects with no safe
  automatic compensation.
- Failed outcomes stay visible as failed receipts even when a low-criticality
  policy fail-opens and allows continuation.
- Microsoft Agent Framework support now has two paths: a native optional
  integration for real MAF async/middleware seams and the original
  dependency-light MAF-shaped callable fallback.
- Verified MAF API seam on 2026-06-25 from official Microsoft sources:
  `agent-framework-core` installs from PyPI, supports Python 3.10+, exposes
  `agent_framework.Agent`, `Agent.run(...)`, async middleware, `BaseChatClient`,
  and `ChatResponse`. The package remains optional behind the `microsoft`
  extra; provider packages such as Foundry or OpenAI can be installed by user
  apps when needed.
- Benchmark results are scenario-suite results only; they should not be framed
  as universal reliability guarantees.
- The README uses the human-supplied architecture image at
  `assets/architecture.png`.
- The architecture image uses compact presentation labels; the source of truth
  remains the structured receipt JSON documented in `docs/diagram-receipt-map.md`.
  `Freshness` is the public diagram label for state freshness checks.
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
- GitHub Actions runs `python -m pytest`; keep `pythonpath = ["src", "."]` in
  `pyproject.toml` so the current checkout wins over stale editable installs
  and top-level helper packages like `benchmark/` import on Linux CI.

## Next
- Maintain benchmark/docs sync on future changes.
- Future, not now: deeper native LangGraph/CrewAI/AutoGen/Azure Durable/OpenAI
  Agents SDK packages, hosted community leaderboard automation, signed
  receipts, richer graph visualization, and legal-review-specific compliance
  templates.

## Open questions for the human
- None.
