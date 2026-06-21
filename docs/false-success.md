# False-Success Bugs

A false-success bug happens when an agent says the job is done before the real
world agrees.

The canonical story:

> Your refund agent called the payment API. The API returned 200 OK. The
> provider status was still `pending`. The agent was about to email "your refund
> is complete." `agent-consistency` blocks the message and records why.

This class of bug is easy to miss because the trace can look green. The agent
called the tool. The tool returned. The model produced a plausible customer
message. The bug lives in the gap between tool success and verified outcome.

## Sub-Types

- **Tool success without outcome success:** an API returns but the authoritative
  status is still `pending`.
- **Stale-state success:** an agent approves from an outdated policy snapshot.
- **Thin-handoff success:** a downstream agent acts without required facts.
- **Unsupported-claim success:** a customer message claims completion without
  evidence for that claim.

## Why Traces And Evals Miss It

Traces show what happened. They do not decide whether the workflow was allowed
to continue.

Evals score what was said. They do not verify that a live business outcome
became true.

Structured output validation checks shape. It does not prove the provider
settled the refund, the policy snapshot was current, or the handoff carried the
facts the next agent needed.

## What agent-consistency Adds

`agent-consistency` adds receipts and gates around:

- state reads
- state freshness
- handoff contracts
- proof artifacts
- outcome verification
- customer-visible claims

When a gate fails, the workflow blocks unsafe continuation and records the
reason in a receipt. That gives developers a portable incident artifact instead
of a vague "the agent lied" report.
