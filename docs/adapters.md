# Adapters

Adapters wrap framework-style callables with receipt-backed steps. They do not
install the frameworks themselves. The core package remains dependency-free.

## LangGraph-Style Nodes

```python
from agent_consistency import detect_risks
from agent_consistency.adapters import LangGraphConsistencyAdapter

adapter = LangGraphConsistencyAdapter.detect("refund-graph")

refund_node = adapter.wrap_node(
    node,
    name="refund-node",
    action="issue_refund",
    outcome_name="refund_settled",
    outcome_check=lambda result: result["refund"]["status"] == "settled",
)

state = refund_node(state)
report = detect_risks(adapter.receipts())
```

Use `pass_step=True` when the node needs direct access to `read_state`,
`handoff`, or `proof_artifact`.

## CrewAI-Style Tools And Tasks

```python
from agent_consistency.adapters import CrewAIConsistencyAdapter

adapter = CrewAIConsistencyAdapter.detect("refund-crew")

refund_tool = adapter.wrap_tool(
    issue_refund,
    name="issue-refund",
    outcome_name="refund_settled",
    outcome_check=lambda refund: refund["status"] == "settled",
)

refund = refund_tool(order_id="ord_1")
```

The wrapper is just a Python callable. Use it around CrewAI tools, task
callbacks, or any callable that represents a side-effecting step.

## AutoGen-Style Handlers

```python
from agent_consistency.adapters import AutoGenConsistencyAdapter

adapter = AutoGenConsistencyAdapter.detect("refund-chat")

reply = adapter.wrap_handler(
    refund_reply_handler,
    agent="refund-agent",
    action="send_customer_message",
    outcome_name="supported_customer_reply",
    outcome_check=lambda result: result["supported"] is True,
)

message = reply(messages)
```

Use the adapter around reply functions, tool handlers, or group-chat callbacks.

## Why Interfaces First

LangGraph, CrewAI, and AutoGen have different object models and version churn.
These adapters expose the stable part: wrapping a callable step, attaching a
receipt, and verifying the outcome that matters. Framework-specific sugar can
grow from this interface without adding heavy dependencies to the base install.
