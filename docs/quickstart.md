# Quickstart

Install the package:

```bash
python -m pip install agent-consistency
```

## Add One Outcome Gate

```python
from agent_consistency import WorkflowRun

run = WorkflowRun("refund-ord-1")

with run.step("refund-agent", "issue_refund", step_id="refund") as step:
    provider_result = {"refund_id": "rf_1", "status": "pending"}
    step.write_state("refund", provider_result, include_value=True)
    step.verify_outcome(
        "refund_settled",
        lambda: provider_result["status"] == "settled",
        failure_reason="refund provider did not confirm settlement",
        details=provider_result,
    )
```

In the default mode, a failed outcome raises before downstream continuation. In
`record` or `report` mode, the failed gate is recorded without raising.

## Try Detect Mode First

```python
from agent_consistency.integrations import detect_workflow

risk_report = detect_workflow(existing_workflow)
print(risk_report.to_dict())
```

Detect mode is useful when you want a report before changing orchestration
control flow.

## Inspect Receipts

```bash
agent-consistency report runs/demo/receipts.jsonl
agent-consistency detect runs/demo/receipts.jsonl
agent-consistency verify runs/demo/receipts.jsonl
```

Use `report` for a readable summary, `detect` for false-success risk, and
`verify` for receipt integrity.
