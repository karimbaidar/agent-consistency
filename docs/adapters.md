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

## Microsoft Agent Framework-Shaped Agents

Use the native integration for real Microsoft Agent Framework async and
middleware seams:

```python
from agent_consistency.integrations import MicrosoftAgentFrameworkNativeIntegration

integration = MicrosoftAgentFrameworkNativeIntegration(run_id="refund-maf")
refund_agent = integration.wrap_agent_run(
    maf_refund_agent,
    action="issue_refund",
    criticality="financial",
    outcome_name="refund_settled",
    outcome_check=lambda result: result["status"] == "settled",
)

refund = await refund_agent({"refund_id": "rf_1"})
```

Install with `agent-consistency[microsoft]` on Python 3.10+ when you want the
real Microsoft Agent Framework core package. The base install remains
dependency-free.

The native integration also exposes `agent_middleware(...)`,
`function_middleware(...)`, and `wrap_agent_stream(...)`; see
[Microsoft Agent Framework](microsoft-agent-framework.md).

Use the dependency-light fallback when you cannot or do not want to install
Microsoft packages:

```python
from agent_consistency.integrations import MicrosoftAgentFrameworkConsistencyAdapter

adapter = MicrosoftAgentFrameworkConsistencyAdapter(run_id="refund-maf")

refund_agent = adapter.wrap_agent_method(
    maf_refund_agent,
    method="invoke",
    action="issue_refund",
    criticality="financial",
    outcome_name="refund_settled",
    outcome_check=lambda result: result["status"] == "settled",
)

refund = refund_agent({"refund_id": "rf_1"})
```

The fallback adapter is dependency-light: it wraps MAF-shaped methods and callables
without importing Microsoft Agent Framework in the base package. Install
`agent-consistency[microsoft]` for the native integration surface; the fallback
does not require extra runtime packages.

Use `record_handoff(...)` when you want to preserve a MAF-style transfer before
the downstream agent runs:

```python
packet = adapter.record_handoff(
    from_agent="intake-agent",
    to_agent="refund-agent",
    task="issue refund",
    facts={"order_id": "ord_1", "amount": 42.5},
    required_facts=["order_id", "amount"],
)
```

## Instrument An Existing Agent

The fastest path is often to wrap one existing side-effecting method:

```python
from agent_consistency import RefundSettlementVerifier, WorkflowRun, verified_step

run = WorkflowRun("refund-ord-1")
agent.issue_refund = verified_step(
    run,
    "refund-agent",
    "issue_refund",
    criticality="financial",
    outcome_verifier=lambda result: RefundSettlementVerifier(
        result["refund"]["refund_id"],
        agent.provider_lookup,
    ),
)(agent.issue_refund)
```

See `examples/instrument_existing_agent/` for the before/after version that runs
in CI.

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

LangGraph, CrewAI, AutoGen, and Microsoft Agent Framework have different object
models and version churn. These adapters expose the stable part: wrapping a
callable step, attaching a receipt, and verifying the outcome that matters.
Framework-specific sugar can grow from this interface without adding heavy
dependencies to the base install. Additional adapters, including deeper
LangGraph, CrewAI, AutoGen, Azure Durable, and OpenAI Agents SDK integrations,
are future work and should follow `skills/add-framework-adapter/SKILL.md`.
