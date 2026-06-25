# Instrument Existing Agent

This example shows the 10-minute path: keep the existing agent and wrap the one
side-effecting step that makes a business-visible claim.

Run the unsafe baseline:

```bash
python examples/instrument_existing_agent/before.py
```

Run the protected version:

```bash
python examples/instrument_existing_agent/after.py
```

The relevant change is the wrapper in `after.py`:

```python
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

The wrapper records a receipt and re-checks provider ground truth before the
workflow can claim the refund is complete.

