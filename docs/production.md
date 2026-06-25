# Production Notes

`agent-consistency` is intentionally small: the core package has no required
runtime dependencies and stores receipts through a simple `ReceiptStore`
interface. Production use should make the continuation policy explicit around
each side effect.

## Continuation Policy

`WorkflowRun` defaults to `on_violation="raise"`. Use that mode when a failed
state, handoff, claim, or outcome check should stop downstream continuation.

Other modes are useful during rollout:

- `warn`: emit a `RuntimeWarning` and record the issue.
- `record`: record the issue without raising.
- `report` / `detect`: run non-blocking receipt collection for risk reporting.

For irreversible, financial, customer-visible, or compliance-sensitive actions,
start with blocking behavior and only relax it when the surrounding workflow has
a separate compensating control.

## Outcome Verification

Outcome checks should read ground truth, not the model response. Examples:

- payment provider status for a refund
- database read-after-write for a record update
- support platform lookup for a ticket creation
- policy store version for an approval decision

The outcome verifier should answer the business question the next step depends
on: "is the refund settled?", "does the ticket exist?", or "is this policy
snapshot still current?"

## Receipt Stores

The package ships two stores:

- `InMemoryReceiptStore`: useful in tests, demos, and short-lived workflows.
- `JsonlReceiptStore`: writes one JSON receipt per line and creates parent
  directories automatically.

Both stores deduplicate receipt keys by `run_id:step_id` by default. JSONL
receipts include a digest chain when they are written through the store, so
`agent-consistency verify` can detect edits and reordering.

For production retention, rotate and archive JSONL files with your existing log
or artifact pipeline. Keep receipt files out of `.env` and secret-bearing paths;
receipts may include state digests, metadata, and optional included values.

## Hot Path Guidance

Contract checks are synchronous because they guard the next workflow step. Keep
checks cheap:

- compare versions or digests for state freshness
- validate required handoff facts before downstream work starts
- query the smallest authoritative outcome needed for continuation
- keep large payloads out of receipts unless `include_value=True` is necessary

If a provider check is slow or flaky, decide at the workflow level whether the
safe behavior is to block, retry, ask for human approval, or continue in a
non-blocking rollout mode.

## CLI Checks

Use the CLI in CI or incident review:

```bash
agent-consistency report runs/demo-pending-refund/receipts.jsonl
agent-consistency detect runs/demo-pending-refund/receipts.jsonl
agent-consistency verify runs/demo-pending-refund/receipts.jsonl
```

`detect` reports false-success risk from declared receipts. It cannot infer
claims or outcomes your workflow did not record.

