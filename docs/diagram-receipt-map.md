# Diagram To Receipt Map

The README architecture image is a compact visual summary. Labels such as
`state_ok=true`, `handoff_ok=true`, and `outcome_ok=true` are presentation
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

The expected interpretation is a verified receipt chain with a failed run:
`refund_settled` is false, the policy decision is `fail_closed`, and the action
is blocked.

## Field Mapping

| Diagram label | Receipt field |
| --- | --- |
| `tool_result=200 OK` | Optional metadata on `state_deltas[]` or your own recorded state. The sample records it at `state_deltas[0].metadata.tool_result`. |
| `state_ok=true` | `state_reads[]`, `state_deltas[]`, and absence of state-related `issues[]`. Failed freshness checks appear as issues and set `status` to `failed`. |
| `handoff_ok=true` | `handoffs[]`, `produced_handoff_ids[]`, `consumed_handoff_ids[]`, and absence of handoff-related `issues[]`. Missing facts or evidence are explicit issues. |
| `evidence_present=true` | `proof_artifacts[]`, especially `verified`, `digest`, `uri`, and `verifier`, plus any consumed artifact IDs. |
| `refund_settled=true` / `refund_settled=false` | `outcomes[]` entries where `name` is `refund_settled` and `passed` is `true` or `false`. |
| `policy_version_ok=false` | A state freshness failure: `state_reads[].version` disagrees with the current version and an issue records the stale state. |
| `ALLOW` | Receipt `status` is `passed`, or the policy decision records a fail-open warning that allows continuation. |
| `BLOCK` | Receipt `status` is `failed` with an error issue and a `policy_decisions[]` entry such as `mode: fail_closed`. |

## Event Shorthand

The receipt trail in the image uses event names for readability:

| Image event | Receipt section |
| --- | --- |
| `state.read` | `state_reads[]` |
| `handoff.sent` | `handoffs[]` and `produced_handoff_ids[]` |
| `handoff.checked` | `consumed_handoff_ids[]`, verifier results, and handoff issues |
| `outcome.verify` | `outcomes[]` |
| `action.blocked` | `status: failed`, `issues[]`, and `policy_decisions[]` |

This lets the image stay readable while the receipt JSON stays durable,
schema-backed, and suitable for verification.
