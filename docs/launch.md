# Launch Kit

Use the live demo link in every launch surface:

https://karimbaidar.github.io/false-success-lab/

## Show HN

Title options:

- Show HN: agent-consistency - stop agents from saying done before the world agrees
- Show HN: A flight recorder and gate layer for false-success bugs in AI agents
- Show HN: Detect when agent workflows continue after failed real-world outcomes

First comment:

```text
I built agent-consistency to catch a class of agent bug I kept seeing: the tool
call succeeds, but the business outcome is still false.

Canonical example: a refund API returns 200 OK, provider status is still
pending, and the agent is about to email "your refund is complete."

The live demo shows the naive flow versus the protected flow:
https://karimbaidar.github.io/false-success-lab/

The package adds receipts and gates for state freshness, handoffs, proof
artifacts, and outcome verification. It is not a tracing replacement. Traces
show what happened. Evals score what was said. agent-consistency decides whether
the workflow was allowed to continue.
```

## X / Twitter Thread

```text
1/ AI agents are starting to take real actions: refunds, approvals, account
updates, customer emails.

That creates a new bug class: false-success bugs.

The agent says "done" before the real world agrees.

2/ Example:

Refund API returns 200 OK.
Provider status is still pending.
Agent is about to email: "your refund is complete."

The tool call succeeded. The outcome did not.

3/ Traces show what happened.
Evals score what was said.
Output validation checks shape.

None of those decide whether the workflow was allowed to continue.

4/ I built agent-consistency as a receipt and gate layer for this gap.

It records state reads, handoff facts, proof artifacts, and outcome checks.
If the outcome is false, the unsafe continuation gets blocked.

5/ Try the live demo. It takes about 10 seconds:
https://karimbaidar.github.io/false-success-lab/

Run "Pending refund" and watch the customer message get blocked.
```

## LinkedIn

```text
Agent reliability is becoming a liability problem, not a prompt problem.

When an AI agent sends a customer email, issues a refund, approves a change, or
updates an account, a green trace is not enough. The workflow needs evidence
that the real-world outcome became true before the agent makes a claim.

I built agent-consistency to catch "false-success bugs": cases where a tool call
succeeds but the business outcome is still false.

Example: the refund API returns 200 OK, but provider status is still pending.
The agent is about to email "your refund is complete." agent-consistency blocks
the message and records why.

Live demo:
https://karimbaidar.github.io/false-success-lab/
```

## Reddit r/LocalLLaMA

```text
[P] Detect false-success bugs in local or hosted agent workflows

I built a zero-dependency Python package called agent-consistency. It adds
receipts and gates around agent workflows so a workflow can prove the real-world
outcome happened before continuing.

The motivating bug: refund API returns 200 OK, provider status is still pending,
agent emails "your refund is complete."

Live demo:
https://karimbaidar.github.io/false-success-lab/

Repo:
https://github.com/karimbaidar/agent-consistency
```

## Reddit r/AI_Agents

```text
[P] agent-consistency: receipts and gates for false-success bugs

As agents move from chat into actions, I think one bug class needs a name:
false-success bugs. The workflow says done before the world agrees.

This package records receipts for state reads, handoffs, evidence, and outcome
checks. Detect mode can report missing gates and customer-visible actions after
failed outcomes without blocking the workflow.

Demo:
https://karimbaidar.github.io/false-success-lab/
```

## Reddit r/MachineLearning

```text
[P] False-success bugs in agent workflows: outcome gates and portable receipts

This is a small Python package for runtime agent reliability. It is not an eval
framework and not a tracing backend. It records inspectable receipts and checks
whether workflow continuation is allowed after mutable state reads, handoffs,
and side-effecting actions.

The demo focuses on a refund workflow where the API call succeeds but the
provider status is still pending:
https://karimbaidar.github.io/false-success-lab/
```

## Newsletter Pitch

```text
agent-consistency is a zero-dependency Python library for a sharp new agent
reliability category: false-success bugs, where an agent says the job is done
before the real world agrees. The live demo shows a refund API returning 200 OK
while provider status is still pending; the protected workflow blocks the
customer email and records a receipt explaining why.
```

## Distribution Note

Ship the live demo first. Post Show HN with the demo link. Then go deep in one
community for weeks. Look for threads where people say their agent lied, skipped
a check, used stale state, or sent the wrong customer message. Reply with the
name of the category: "That is a false-success bug." Then link the 10-second
demo.

Traction here is sustained distribution multiplied by time, not one launch post.
