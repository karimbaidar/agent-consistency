# Microsoft Agent Framework

`agent-consistency` has two Microsoft Agent Framework paths:

- `MicrosoftAgentFrameworkNativeIntegration`: native async integration surface
  for real MAF agents, middleware, function/tool middleware, and streams.
- `MicrosoftAgentFrameworkConsistencyAdapter`: dependency-light fallback for
  MAF-shaped callables.

The base install stays dependency-free. Install the Microsoft extra only where
the real framework is needed:

```bash
python -m pip install "agent-consistency[microsoft]"
```

The Microsoft `agent-framework` package currently requires Python 3.10+, so the
extra is marked for Python 3.10+ while the core package still supports Python
3.9+.

## Verified API Seam

The native integration targets the documented Python seams in Microsoft Agent
Framework:

- `agent_framework.Agent`
- `await agent.run(...)`
- async agent middleware with `(context, call_next)`
- function/tool middleware using `FunctionInvocationContext`
- streaming and workflow samples

It does not import Microsoft packages at module import time. User code imports
MAF and passes real agents or middleware registration points into the
integration.

## Wrap Agent.run

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

Use `result_extractor` when the MAF result object wraps the business payload,
for example when the useful value lives on `result.text` or another property.

## Agent Middleware

```python
integration = MicrosoftAgentFrameworkNativeIntegration()

consistency_middleware = integration.agent_middleware(
    agent="refund-agent",
    action="issue_refund",
    criticality="financial",
    outcome_name="refund_settled",
    result_extractor=lambda context: context.result,
    outcome_check=lambda result: result["status"] == "settled",
)
```

Attach that middleware through MAF's `middleware=[...]` registration. The
integration maps common context fields such as `run_id`, `session_id`,
`thread_id`, and `invocation_id` into receipt metadata. If a context supplies a
run identifier, receipts are stored under that run; otherwise the integration's
default `WorkflowRun` is used.

## Function And Tool Middleware

```python
tool_middleware = integration.function_middleware(
    agent="refund-tool",
    criticality="financial",
    idempotency_key=lambda context: f"refund:{context.invocation_id}",
    outcome_name="refund_settled",
    outcome_check=lambda result: result["status"] == "settled",
)
```

The middleware names the receipt action from `context.function.name` when MAF
provides it.

## Streaming

```python
refund_stream = integration.wrap_agent_stream(
    maf_refund_agent,
    action="issue_refund_stream",
    criticality="financial",
    outcome_name="refund_settled",
    stream_result_reducer=lambda chunks: chunks[-1],
    outcome_check=lambda result: result["status"] == "settled",
)

async for chunk in refund_stream({"refund_id": "rf_1"}):
    ...
```

Chunks are yielded as they arrive. The gate verifies the reduced final result
after the stream completes, so a pending refund still becomes a failed receipt
and blocks the unsafe continuation.

## Fallback Adapter

Use `MicrosoftAgentFrameworkConsistencyAdapter` when you only have a MAF-shaped
callable or cannot install Microsoft packages. It remains dependency-light and
continues to wrap sync callables, agent-like methods, and handoff records.
