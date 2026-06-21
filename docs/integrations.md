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
