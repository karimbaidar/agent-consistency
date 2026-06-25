# Receipts

Receipts are a flight recorder for AI agent workflows. Each receipt records what
an agent step read, which facts it handed off, which evidence it attached, which
outcomes it checked, and why a gate passed or blocked continuation.

Receipts make workflow claims inspectable after the run. They are not a formal
proof system, and they do not prove an agent was globally correct. They make the
specific state, handoff, artifact, and outcome claims portable enough to review
in CI, incident response, audit, or debugging.

## Tamper-Evident Chains

New receipts include:

- `schema_version`
- `receipt_id`
- `previous_receipt_digest`
- `receipt_digest`

`receipt_digest` is computed from the canonical JSON form of the receipt with
the `receipt_digest` field excluded. `previous_receipt_digest` commits each
receipt to the receipt before it in the JSONL file. Editing a receipt or
reordering receipts changes the verification result.

This is hash-chained tamper evidence, not a cryptographic signature. It detects
edits and reordering against the stored chain; it does not prove authorship or
stop someone with write access from replacing the entire file and recomputing a
new chain. Signed receipts remain future work.

The canonical JSON implementation uses the package's existing `stable_json` and
`stable_digest` helpers.

## Verify A Receipt File

```bash
agent-consistency verify runs/demo-pending-refund/receipts.jsonl
```

The command separates two questions:

- **Integrity:** is the file structurally valid, internally consistent, and
  tamper-evident when a digest chain is present?
- **Run status:** did the workflow pass, or did a gate fail as expected?

A deliberately blocked run can have verified integrity.

## Sample: Happy Path

```text
Receipt verification: runs/demo-happy-refund/receipts.jsonl
Receipts: 5
Integrity: verified
Run status: passed
Structural checks: passed
Digest chain: verified

Result: OK
```

## Sample: Pending Refund

The tracked sample file is
`docs/samples/pending-refund-receipts.jsonl`.

```text
Receipt verification: docs/samples/pending-refund-receipts.jsonl
Receipts: 1
Integrity: verified
Run status: failed as expected - 1 blocked receipt(s)
Structural checks: passed
Digest chain: verified

Semantic interpretation:
- [semantic] at demo-pending-refund:04-refund: blocked gate - refund_settled failed
- [semantic] at demo-pending-refund:04-refund: outcome refund_settled failed - refund status is pending, not settled

Result: OK
```

## Sample: Tamper

```text
Receipt verification: runs/demo-pending-refund/receipts.jsonl
Receipts: 4
Integrity: failed
Run status: failed as expected - 1 blocked receipt(s)
Structural checks: passed

Errors:
- [integrity] at demo-pending-refund:04-refund: digest mismatch (stored 7df2a9817d9c, computed b82c20a19f40)

Semantic interpretation:
- [semantic] at demo-pending-refund:04-refund: blocked gate - refund_settled failed

Result: FAILED
```

## Schema

Print the packaged receipt JSON Schema:

```bash
agent-consistency schema
```

The schema is packaged at
`agent_consistency/schemas/receipt.schema.json`.
