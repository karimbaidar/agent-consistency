# Why agent-consistency

Agents are moving from chat into workflows that take actions: refunds,
approvals, account changes, customer messages, ticket updates, and operational
handoffs. Once a workflow affects the world, a green model response is not
enough.

The workflow needs to know whether it is allowed to continue.

## The Gap

Most stacks already have useful pieces:

- output validators check response shape
- tracing systems record the path taken
- evals score behavior offline
- orchestration frameworks run the next node
- policy engines decide domain rules

Those tools are still worth using. The gap is the runtime gate that says:

> this step has the right state, the right handoff facts, the right evidence,
> and the real-world outcome was verified, so continuation is allowed.

Without that gate, a customer can be told a refund completed while the provider
still says `pending`.

## Receipts As Infrastructure

Receipts are durable, portable records for serious agent workflows. Store them
as JSONL. Attach them to CI artifacts. Keep them with incident reports. Send
them to auditors or platform teams when someone asks why an agent continued.

They are not a formal proof system. They are inspectable evidence about the
workflow's claims.

## When To Use It

Use `agent-consistency` where an agent:

- reads mutable business state
- hands context to another agent or node
- calls a side-effecting tool
- makes a customer-visible claim
- depends on an approval or proof artifact
- needs post-incident reconstruction

The cost of missing this bug is concrete: a false customer promise, a double
refund, a stale-policy approval, or an incident where the team cannot reconstruct
which facts the agent relied on.
