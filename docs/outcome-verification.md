# Outcome Verification

Outcome verification checks whether the real-world condition became true after
an agent took a side effect.

The core false-success example:

1. A refund agent calls the payment provider.
2. The API returns successfully.
3. The provider status is still `pending`.
4. The agent is about to tell the customer the refund is complete.
5. `agent-consistency` blocks the message because `refund_settled` failed.

Tool success is not business success. Outcome verification is the gate between
"the call returned" and "the workflow may claim completion."

## Minimal Pattern

```python
from agent_consistency import WorkflowRun

run = WorkflowRun("refund-ord-1", on_violation="record")

with run.step("refund-agent", "issue_refund", step_id="refund") as step:
    provider_result = {"refund_id": "rf_1", "status": "pending"}
    step.write_state("refund", provider_result, include_value=True)
    step.verify_outcome(
        "refund_settled",
        lambda: provider_result["status"] == "settled",
        failure_reason="refund provider did not confirm settlement",
        details=provider_result,
    )
```

The receipt records the failed outcome and the blocked reason. In `raise` mode,
the workflow raises before downstream continuation. In `record` mode, the
receipt records the failed gate without raising, which is useful for demos and
analysis.

## Ground-Truth Verifier

For refund workflows, use the built-in provider-status verifier:

```python
from agent_consistency import RefundSettlementVerifier, WorkflowRun

provider_status = lambda refund_id: {"refund_id": refund_id, "status": "pending"}

run = WorkflowRun("refund-ord-1")
with run.step("refund-agent", "issue_refund", step_id="refund") as step:
    step.verify_outcome_with(
        RefundSettlementVerifier("rf_1", provider_status),
        criticality="financial",
    )
```

The verifier re-queries the provider-facing source of truth. If the provider
times out or returns a non-settled status, the failure resolves through the
step's fail-open / fail-closed policy and is recorded in the receipt.

## What To Verify

Verify outcomes that make customer-visible or business-visible claims true:

- refund is settled
- email was sent
- ticket exists
- approval record exists
- account access changed
- shipment cancellation completed
- database write is visible from the source of truth

The outcome should read the authoritative system, not just the model response.

## What Receipts Provide

Receipts capture:

- outcome name
- pass/fail result
- reason
- details from the authoritative check
- timestamp
- issue created by the failed gate

They make the workflow claim inspectable. They do not replace provider
idempotency, transactional guarantees, human approvals, or domain-specific
policy controls.
