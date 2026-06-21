# Bug Zoo

The bug zoo is the canonical set of false-success examples. Each script is under
40 lines and prints the receipt plus the block reason.

Run them from the repo root:

```bash
PYTHONPATH=src python examples/refund_false_success.py
```

## Examples

- `examples/minimal_outcome_gate.py`: a tool returns but the postcondition is
  still false.
- `examples/refund_false_success.py`: the refund API call returns but provider
  status is `pending`.
- `examples/handoff_contract.py`: a required handoff fact is missing.
- `examples/stale_state.py`: approval uses policy v12 while v14 is current.
- `examples/customer_message_supported_claims.py`: a customer-visible claim has
  no supporting fact or evidence.

These examples are intentionally small. They are category builders, not demo
apps.
