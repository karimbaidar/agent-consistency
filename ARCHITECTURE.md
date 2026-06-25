# Architecture

`agent-consistency` is a runtime reliability layer for false-success bugs: the
tool call returned, but the real-world outcome did not happen.

The package does not replace tracing, evals, guardrails, provider idempotency, or
domain policy. It adds a continuation gate and receipt trail around agent steps
that make business-visible claims.

## Verification Model

Each `WorkflowRun` is made of `AgentStep` receipts. A step can record:

- state reads, including version and digest
- state writes
- proof artifacts
- produced and consumed handoffs
- deterministic outcome checks
- policy decisions and issues

The gate checks three kinds of consistency:

- **State:** a step may compare the snapshot it read with the current source of
  truth before writing or approving.
- **Handoff:** a downstream step may require facts, constraints, assumptions,
  evidence, verified artifacts, and contract-specific verifier results.
- **Outcome:** a side-effecting step may re-query ground truth before letting the
  workflow claim completion.

Outcome checks must read an authoritative system. The core path must not use a
model as its own judge.

## Gate And Receipt Flow

1. A workflow creates `WorkflowRun(run_id, on_violation=...)`.
2. Each agent action runs inside `run.step(...)`, `reliability_gate(...)`, or a
   lightweight adapter wrapper.
3. Checks append structured evidence to the current receipt.
4. Failures are resolved through `FailurePolicy` using explicit criticality.
5. Fail-closed decisions block by raising in blocking modes; fail-open decisions
   are recorded as warnings and allow rollout to continue.
6. Receipts are stored through `ReceiptStore`. JSONL receipts carry digest-chain
   fields so `agent-consistency verify` can detect edits and reordering.

## Extension Points

- `OutcomeVerifier` and concrete verifier classes in `outcome.py`.
- `ReceiptStore`, `BufferedReceiptStore`, `JsonlReceiptStore`,
  `PostgresReceiptStore`, and `OtelReceiptExporter` in `store.py`.
- `verified_step(...)` and `reliability_gate(...)` in `api.py`.
- Dependency-light adapters in `adapters/` and `integrations/`.
- Deterministic benchmark scenarios in `benchmark/`.

## OpenTelemetry Mapping

OpenTelemetry support is optional. `reliability_gate(...)` uses an injected
tracer when supplied, otherwise it imports OpenTelemetry lazily. If OTel is not
installed, the gate still works and emits no spans. When enabled, the API emits
spans with standard `gen_ai.*` attributes plus `agent_consistency.*` receipt
attributes:

- `gen_ai.operation.name`
- `gen_ai.system`
- `agent_consistency.run_id`
- `agent_consistency.step_id`
- `agent_consistency.agent`
- `agent_consistency.action`
- `agent_consistency.status`
- `agent_consistency.criticality`
- `agent_consistency.policy.mode`

The core package works without OTel installed.

## Production Invariants

- Ground-truth outcome checks only; no model self-judging in the core path.
- Irreversible and financial actions default fail-closed.
- Contract checks stay cheap and synchronous.
- Receipt writes can be buffered and flushed at blocking decisions.
- Required dependencies stay at zero for the core package.
- Optional integrations stay behind extras.
