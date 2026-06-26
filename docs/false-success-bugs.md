# False-Success Bugs

## When an agent reports completion before the source system confirms the result

A false-success bug happens when an AI agent reports completion even though the
confirmed result is still false, unresolved, stale, unsupported, or missing.

The bug is not that the model hallucinated a random fact. The bug is sharper:
the workflow took an action, saw something that looked successful, and continued
as if the business condition had become true.

The refund story is the cleanest version:

> Your refund agent called the payment API. The API returned 200 OK. The
> provider status was still `pending`. The agent was about to email "your refund
> is complete." `agent-consistency` blocks the message and records why.

That is a false-success bug. The tool call succeeded. The outcome did not.

## Why this bug is spreading

Agents are moving from chat into workflows that change source-system state:
refunds, account updates, approvals, customer messages, support tickets,
scheduling, operations, and compliance handoffs.

Once an agent can take side effects, the old success signals are too weak.

- The HTTP call returned.
- The trace is green.
- The model output matched the JSON schema.
- The next node ran.

None of those prove that the customer got the refund, the account permission
changed, the policy snapshot was current, or the handoff carried the facts the
next agent needed.

False-success bugs live between "the workflow moved" and "the source system
confirmed the result."

## The main sub-types

### Tool success without outcome success

The API returns 200 OK, but the authoritative system still says `pending`,
`queued`, `processing`, or `not_found`.

This is the refund bug. It is also the ticket-closed bug, the shipment-canceled
bug, and the "database write returned but replica read cannot see it" bug.

The cost is a customer-visible promise that is not true.

### Stale-state success

The agent reads policy v12, then approves under that policy while v14 is
current.

The trace can show exactly what happened and still miss the safety question:
was the state fresh at the moment of action?

The cost is a decision recorded against rules the business no longer accepts.

### Thin-handoff success

Agent A hands work to Agent B without the required facts, such as previous
refund count, fraud score, source-of-truth ID, jurisdiction, or approval limit.

Agent B may produce a polished answer. The workflow may continue. The decision
is still built on missing context.

The cost is a downstream action that cannot be defended after the incident.

### Unsupported-claim success

A customer-facing message claims "refund complete" or "your account has been
updated" without evidence for that exact claim.

The model output can be fluent and formatted. The claim is still unsupported.

The cost is a written promise the system cannot back up.

### Action after unresolved outcome

The workflow records a failed or missing outcome, then still performs a
customer-visible action.

This is the failure mode detect mode is designed to expose first. It does not
need to know every internal claim. It only needs to see that an unresolved gate
was followed by an action that reaches the customer.

The cost is a workflow that knew enough to be suspicious and continued anyway.

## Why output validation misses it

Output validation answers a useful question: did the model produce the shape we
expected?

It does not answer whether the source system confirmed the result.

Valid JSON can say:

```json
{"message": "Your refund is complete."}
```

That shape can be perfect while the provider status is still `pending`.

## Why tracing misses it

Tracing answers another useful question: what happened?

It can show the refund call, the returned response, the downstream email step,
and the timing of each node.

But a trace is usually observational. It records the path. It does not decide
whether the workflow was allowed to continue.

The missing primitive is a gate.

## What agent-consistency adds

`agent-consistency` records receipts and enforces gates around workflow claims.

It can record:

- state reads and state freshness checks
- handoff facts and required fields
- proof artifacts and evidence references
- outcome checks against authoritative systems
- customer-visible claims and their support
- digest-chained receipts for later inspection

When a gate fails, the workflow can block continuation. In detect mode, it can
report the same risk without blocking so teams can find bugs before refactoring.

## Try the bug in 10 seconds

Open the live demo:

[Watch a false-success bug get blocked](https://karimbaidar.github.io/false-success-lab/)

Run the **Pending refund** scenario. The naive flow sends the completed-refund
message. The protected flow blocks the message because `refund_settled` was not
verified.

That is the category in one frame: the tool returned, but the confirmed result
was still missing.

## The practical rule

When an agent is about to make a customer-visible or business-visible claim,
ask:

> What outcome would make this claim true, and where is the receipt that proves
> the workflow checked it?

If the answer is "the tool returned," you have a false-success bug waiting to
happen.
