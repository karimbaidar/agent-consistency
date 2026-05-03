# Marketing Playbook

## Positioning

Primary hook:

> Your agent said "refund completed." The payment provider still said "pending."
> agent-consistency catches that before the customer gets lied to.

`agent-consistency` is a reliability layer for side-effecting agent workflows.
It validates state, handoffs, and outcomes before agents continue.

Target users:

- engineers building multi-agent workflows
- AI platform teams
- support automation teams
- payment, approval, and operations workflow owners
- developer relations teams looking for concrete agent reliability demos

## Launch Hooks

- Green traces do not mean the business outcome happened.
- Tool success is not business success.
- Stop AI agents from saying done too early.
- Validate state, handoffs, and outcomes before agents continue.
- Proof before progression for side-effecting agent workflows.

## Screenshot Checklist

- Show the realistic refund support case.
- Show the right-side execution timeline.
- Show the refund provider status as `pending`.
- Show the blocked comms step.
- Show "False success prevented" clearly.
- Show proof artifacts or outcome verification in the trace.

## Demo Recording Checklist

1. Use the refund demo repo.
2. Select `Pending refund`.
3. Record from before clicking `Run workflow`.
4. Keep the timeline visible.
5. Stop after the blocked customer response banner appears.

## X/Twitter

```text
Your agent said "refund completed."
The payment provider still said "pending."

I built agent-consistency to catch that before the customer gets lied to.

It validates state, handoffs, and outcomes before agents continue.
```

## LinkedIn

```text
Agent reliability is not just about better prompts. It is about proving that
each step had the right facts and that the real-world outcome actually happened.

agent-consistency adds lightweight receipts and gates around state reads,
handoffs, and side effects, so workflows can block false success before it
reaches customers.
```

## Reddit

```text
I built a visual refund workflow that blocks AI agents from claiming success too early

The demo shows a multi-agent refund flow where the payment provider returns
pending. The workflow blocks the customer-facing "refund completed" message
until settlement is verified.
```

## Hacker News

Title:

```text
Show HN: A visual demo that catches false-success bugs in AI agent workflows
```

Comment:

```text
Most agent demos stop at tool calls. This one checks whether the business
outcome actually happened. The library is small and framework-agnostic: record
state snapshots, validate handoff contracts, attach proof artifacts, and verify
outcomes before the next agent continues.
```
