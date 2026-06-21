# Detect Mode

Detect mode is the try-before-you-restructure path for teams that already have
an agent workflow. It records receipts and reports false-success risk without
blocking the workflow.

```python
from agent_consistency.integrations import detect_workflow

risk_report = detect_workflow(existing_workflow)
print(risk_report.to_dict())
```

Use the CLI when receipts already exist:

```bash
agent-consistency detect runs/demo-pending-refund/receipts.jsonl
```

The command prints a ranked report and exits non-zero when any high-severity
risk is found, so it can run as a CI check.

## What It Reports

- missing outcome gates on side-effecting actions
- stale state reads
- dropped required handoff facts
- failed outcomes
- customer-visible actions after unresolved or unverified outcomes
- unsupported customer-visible claims

## What It Cannot Know

Detect mode cannot know what an agent privately "claimed" unless the workflow
declares the outcomes, facts, and evidence that matter. A receipt can show that
`refund_settled` failed, or that a customer email ran after that failure. It
cannot infer a missing business postcondition that was never declared.

## LangGraph-Style Nodes

The core package does not depend on LangGraph. The adapter wraps LangGraph-style
node callables and works with mocked or real node functions:

```python
from agent_consistency import detect_risks
from agent_consistency.adapters import LangGraphConsistencyAdapter

adapter = LangGraphConsistencyAdapter.detect("refund-graph")

wrapped_refund = adapter.wrap_node(
    refund_node,
    name="refund-node",
    action="issue_refund",
    outcome_name="refund_settled",
    outcome_check=lambda result: result["refund"]["status"] == "settled",
)

next_state = wrapped_refund(state)
risk_report = detect_risks(adapter.receipts())
```

Use `pass_step=True` when a node needs direct access to `read_state`,
`handoff`, `proof_artifact`, or `verify_outcome`.
