# agent-consistency

Stop agents from saying "done" before the world says "done."

`agent-consistency` adds receipts and gates to agent workflows. It records the
state a step read, the handoff facts it relied on, the evidence it attached,
and the outcomes it verified before the workflow continues.

The canonical false-success bug:

> A refund API returns 200 OK. The provider status is still `pending`. The agent
> is about to email "your refund is complete." `agent-consistency` blocks the
> message and records why.

Traces show what happened. Evals score what was said. `agent-consistency`
decides whether the workflow was allowed to continue.

## Start Here

```bash
python -m pip install agent-consistency
```

```python
from agent_consistency.integrations import detect_workflow

risk_report = detect_workflow(existing_workflow)
print(risk_report.to_dict())
```

Use the live demo when you want the visual story:

[Watch a false-success bug get blocked](https://karimbaidar.github.io/agent-consistency-refund-demo/)

## What To Read

- [Quickstart](quickstart.md): add the first outcome gate.
- [Detect mode](detect-mode.md): report risk without blocking.
- [Verify and tamper evidence](verify-tamper-evidence.md): inspect receipt files.
- [Bug zoo](bug-zoo.md): five concrete false-success examples.
- [Benchmark](benchmark.md): deterministic false-success catch-rate suite.
- [Adapters](adapters.md): Microsoft Agent Framework, LangGraph, CrewAI, and AutoGen-style wrappers.
- [Production notes](production.md): rollout modes, receipt stores, and hot path guidance.
- [Compliance framing](compliance.md): how receipts map onto evidence and oversight needs.
