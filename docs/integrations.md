# Integrations

The core integration helper is dependency-free:

```python
from agent_consistency.integrations import run_gated_step

result = run_gated_step(
    run,
    "refund-node",
    "issue_refund",
    refund_handler,
    outcome_name="refund_settled",
    outcome_check=lambda refund: refund["status"] == "settled",
)
```

Use `detect_workflow` when you want one-call risk reporting:

```python
from agent_consistency.integrations import detect_workflow

risk_report = detect_workflow(existing_workflow)
```

Framework adapters live in `agent_consistency.adapters`. They wrap callable
nodes, tools, or handlers and delegate to the same receipt-backed runtime.

The base package does not install framework dependencies.

## Framework-Agnostic API

Use `reliability_gate` when you want a context manager around an arbitrary
agent step:

```python
from agent_consistency import RefundSettlementVerifier, WorkflowRun, reliability_gate

run = WorkflowRun("refund-ord-1")
provider_status = lambda refund_id: {"refund_id": refund_id, "status": "settled"}

with reliability_gate(
    run,
    "refund-agent",
    "issue_refund",
    criticality="financial",
    idempotency_key="refund:ord_1",
    outcome_verifier=RefundSettlementVerifier("rf_1", provider_status),
) as gate:
    gate.step.write_state("refund", {"refund_id": "rf_1", "status": "settled"})

assert gate.decision.allowed
```

Use `verified_step` when a plain callable is the easiest adoption path:

```python
from agent_consistency import RefundSettlementVerifier, verified_step

@verified_step(
    run,
    "refund-agent",
    "issue_refund",
    criticality="financial",
    outcome_verifier=lambda refund: RefundSettlementVerifier(
        refund["refund_id"],
        provider_status,
    ),
)
def issue_refund():
    return payment_provider.refund("ord_1")
```

OpenTelemetry is optional. When `agent-consistency[otel]` is installed, or when
a tracer is injected, the API emits `gen_ai.*` and `agent_consistency.*` span
attributes for the gate.
