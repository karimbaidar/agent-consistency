# Diagram To Receipt Map

The README architecture image is a compact visual summary. Labels such as
`fresh=true`, `handoff_ok=true`, and `outcome_ok=false` are presentation
shorthand. Stored receipts are the source of truth and use structured JSON
fields, not flat `*_ok` booleans.

## Generated Sample

The pending-refund sample lives at:

```text
docs/samples/pending-refund-receipts.jsonl
```

It is a real JSONL receipt written through `JsonlReceiptStore`, so it includes
`receipt_digest` and `previous_receipt_digest`. Verify it with:

```bash
agent-consistency verify docs/samples/pending-refund-receipts.jsonl
```

The expected interpretation is a verified seven-receipt chain with a failed run:
`state_read`, `handoff_sent`, `handoff_checked`, `tool_call`, `tool_response`,
and `outcome_verify` all record evidence before `decision_blocked` records
`refund_settled=false`, `mode: fail_closed`, and the stopped workflow.

## Field Mapping

| Diagram label | Receipt field |
| --- | --- |
| `Action request: SUCCESS` | `tool_call` receipt plus request proof in `proof_artifacts[]`; success means the API accepted the request, not that the business task finished. |
| `tool_response = SUCCESS (200 OK)` | `tool_response` receipt, with provider response recorded in `state_deltas[]` and `metadata.tool_response`. |
| `idempotency_key=abc123` | `idempotency_key` on the `tool_call` receipt. |
| `fresh=true` | `state_reads[]` plus absence of freshness-related `issues[]`. Failed freshness checks appear as issues and set `status` to `failed`. |
| `handoff_ok=true` | `handoffs[]`, `produced_handoff_ids[]`, `consumed_handoff_ids[]`, and absence of handoff-related `issues[]`. Missing facts or evidence are explicit issues. |
| `outcome_ok=true` / `outcome_ok=false` | `outcomes[]` entries where `name` is `refund_settled` and `passed` is `true` or `false`. |
| `Freshness check` | The freshness portion of `state_reads[]`, versions, digests, and any stale-state issue. |
| `Handoff check` | Handoff production/consumption fields and contract validation evidence. |
| `Outcome check` | Provider status evidence in `proof_artifacts[]` and outcome entries in `outcomes[]`. |
| `ALLOW` | Receipt `status` is `passed`, or the policy decision records a fail-open warning that allows continuation. |
| `BLOCK` | Receipt `status` is `failed` with an error issue and a `policy_decisions[]` entry such as `mode: fail_closed`. |

## Event Shorthand

The receipt trail in the image uses event names for readability:

| Image event | Receipt section |
| --- | --- |
| `state_read` | `state_reads[]` on the `01-state-read` receipt |
| `handoff_sent` | `handoffs[]` and `produced_handoff_ids[]` on the `02-handoff-sent` receipt |
| `handoff_checked` | `consumed_handoff_ids[]`, verifier results, and handoff issues on the `03-handoff-checked` receipt |
| `tool_call` | `idempotency_key`, request metadata, and request proof in `proof_artifacts[]` on the `04-tool-call` receipt |
| `tool_response` | Provider response data in `state_deltas[]` and `metadata.tool_response` on the `05-tool-response` receipt |
| `outcome_verify` | Provider-status proof in `proof_artifacts[]` on the `06-outcome-verify` receipt |
| `decision_blocked` | Failed `outcomes[]`, error `issues[]`, and `policy_decisions[]` on the `07-decision-blocked` receipt |

This lets the image stay readable while the receipt JSON stays durable,
schema-backed, and suitable for verification.
