# agent-consistency

Prevent stale-state, broken-handoff, and false-success bugs in multi-agent workflows.

`agent-consistency` is a small Python library for recording consistency receipts across agent
workflow steps. It is not an agent framework, policy engine, or tracing dashboard. It focuses on a
specific production problem:

> Your agents may be smart, but are they acting on the same version of reality?

Multi-agent systems often fail quietly because an agent reads stale state, receives an incomplete
handoff, retries a side effect, or declares success after a tool returned `200` even though the
business outcome is still not true. This library gives each step an explicit receipt:

- what state was read
- what assumptions were made
- what state changed
- what was handed off
- what postcondition proved success

The core package is generic. Azure Durable Functions is the first adapter because replay, resume,
and orchestration history make these consistency problems especially visible.

## What Is New In 0.2

Version `0.2.0` adds causal consistency features for more realistic agent
systems:

- `HandoffContract` for declared inputs, evidence, produced artifacts, and verifier names
- `ProofArtifact` for verified outputs such as provider reads, decisions, approvals, files, or tickets
- `VerifierRegistry` for dynamic verifier selection without hard-coding every check inline
- `consume_handoff` so downstream agents can reject stale, incomplete, or unverified work
- `build_causality_graph` and `trace_causality` to explain which upstream step a downstream action relied on

The goal is to make “done” mean more than “the last agent stopped talking.”

## Install

From a local checkout:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e ".[dev]"
```

After publishing:

```bash
python -m pip install agent-consistency
```

## Quickstart

```python
from agent_consistency import WorkflowRun

run = WorkflowRun("refund-ord-1")

with run.step("history-agent", "load_order", step_id="history") as step:
    order = {"id": "ord_1", "previous_refund_count": 0, "total": 42.5}
    order_snapshot = step.read_state("order", order, version="order-v3")

    handoff = step.handoff(
        to_agent="eligibility-agent",
        task="decide refund eligibility",
        facts={"order": order, "policy_version": "policy-v12"},
        evidence={"order.previous_refund_count": order_snapshot.to_dict()},
        required_facts=["order.id", "order.previous_refund_count", "policy_version"],
        required_evidence=["order.previous_refund_count"],
    )

with run.step("eligibility-agent", "decide", step_id="eligibility") as step:
    policy = {"max_previous_refunds": 0, "max_amount": 100}
    policy_snapshot = step.read_state("refund_policy", policy, version="policy-v12")
    step.ensure_fresh(policy_snapshot, current_version="policy-v12")

    step.require_supported_claims(
        handoff,
        {"eligible": True},
        by=["order.previous_refund_count"],
    )

with run.step("refund-agent", "issue_refund", step_id="refund") as step:
    provider_result = {"refund_id": "rf_1", "status": "settled"}
    step.write_state("refund", provider_result, version="refund-rf_1")
    step.verify_outcome(
        "refund_settled",
        lambda: provider_result["status"] == "settled",
        details={"refund_id": "rf_1"},
    )

for receipt in run.receipts():
    print(receipt.to_dict())
```

## Core Features

### State Snapshot Guard

Record the exact version and stable hash of state read by an agent step. Before a write, verify the
step is still based on fresh state.

```python
from agent_consistency import WorkflowRun

run = WorkflowRun("policy-run")

with run.step("eligibility-agent", "decide") as step:
    snapshot = step.read_state("refund_policy", {"limit": 100}, version="v12")
    step.write_state(
        "refund_decision",
        {"eligible": True},
        based_on=snapshot,
        current_version="v12",
    )
```

By default, consistency violations raise exceptions. You can also use `on_violation="warn"` or
`on_violation="record"`.

```python
run = WorkflowRun("policy-run", on_violation="record")
```

### Handoff Packet Validator

Make agent-to-agent handoff explicit. Required fields can use dot paths.

```python
packet = step.handoff(
    to_agent="refund-agent",
    task="issue refund",
    facts={"order": {"id": "ord_1", "previous_refund_count": 0}},
    assumptions=["order data came from the primary store"],
    constraints=["do not refund if the customer was already refunded"],
    required_facts=["order.id", "order.previous_refund_count"],
)
```

### Handoff Contracts And Proof Artifacts

Use contracts when a downstream agent should only trust work that declares its
inputs, proof artifacts, and verifier.

```python
from agent_consistency import HandoffContract, WorkflowRun

contract = HandoffContract.define(
    "refund_approval",
    required_facts=["order_id", "amount"],
    produced_artifacts=["policy_decision"],
    verifier="refund_approval_check",
)

run = WorkflowRun("refund-ord-1")

with run.step("policy-agent", "approve", step_id="policy") as step:
    artifact = step.proof_artifact(
        "policy_decision",
        {"eligible": True, "policy_version": "policy-v12"},
        kind="decision",
        verified=True,
        verifier="policy_rule",
    )
    packet = step.handoff(
        to_agent="refund-agent",
        task="issue refund",
        facts={"order_id": "ord_1", "amount": 42.5},
        artifacts=[artifact],
        contract=contract,
    )

with run.step("refund-agent", "issue", step_id="refund") as step:
    step.consume_handoff(packet, contract=contract)
```

### Outcome Verifier

A tool call is not complete just because it returned. Add a postcondition that proves the business
outcome became true.

```python
step.verify_outcome(
    "refund_settled",
    lambda: payment_provider.get_refund("rf_1")["status"] == "settled",
)
```

### Dynamic Verifier Registry

Dynamic verification means the verification strategy can depend on action,
contract, risk, or data. It does not require an LLM.

```python
from agent_consistency import VerifierRegistry

registry = VerifierRegistry()

@registry.register("refund_amount_check")
def refund_amount_check(context):
    return context.facts["amount"] < 500

with run.step("refund-agent", "issue", step_id="refund") as step:
    step.consume_handoff(packet, contract=contract, registry=registry)
```

### Run Diff

Compare two runs and see where state, assumptions, handoffs, deltas, or outcomes diverged.

```python
from agent_consistency import diff_runs

diff = diff_runs(previous_run_receipts, current_run_receipts)
print(diff.summary())
```

### Causality Trace

Build a small graph of which receipts produced the handoffs and artifacts that
later receipts consumed.

```python
from agent_consistency import trace_causality

print(trace_causality(run.receipts()))
```

## Azure Durable Functions Adapter

The Azure Durable adapter has no hard Azure dependency. It works with a Durable orchestration
context-like object and provides:

- Durable instance id as the consistency run id
- replay-safe logging helper
- deterministic activity keys for idempotent side effects
- optional custom status updates with receipt summaries

```python
from agent_consistency.adapters import DurableConsistencyContext, replay_safe_log

def orchestrator_function(context):
    durable = DurableConsistencyContext(context)

    with durable.step("refund-orchestrator", "schedule_refund", step_id="schedule") as step:
        intent = {"order_id": "ord_1", "amount": 42.5}
        activity_key = durable.activity_key("issue_refund", intent)
        step.read_state("refund_intent", intent, version=activity_key)

    durable.set_custom_status()
```


## Status

This is an early library with a stable core direction:

- generic consistency receipts
- Azure Durable Functions as the first adapter
- framework adapters later

The goal is to catch quietly wrong success before it becomes production damage.
