# Verify And Tamper Evidence

Receipts can be stored as JSONL and verified later:

```bash
agent-consistency verify runs/demo-pending-refund/receipts.jsonl
```

The command answers two separate questions:

- **Integrity:** is the receipt file structurally valid, internally consistent,
  and tamper-evident when digests are present?
- **Run status:** did the workflow pass, or did a gate fail as expected?

A failed run is not the same thing as a bad receipt file. A pending refund can
be blocked correctly and still have verified integrity.

## Digest Chain

Each stored receipt can include:

- `schema_version`
- `receipt_id`
- `previous_receipt_digest`
- `receipt_digest`

The digest is computed from canonical JSON with `receipt_digest` excluded. Each
receipt commits to the digest of the previous receipt, so edits and reordering
are detectable.

## Schema

Print the packaged JSON Schema:

```bash
agent-consistency schema
```

The schema is shipped with the package at
`agent_consistency/schemas/receipt.schema.json`.
