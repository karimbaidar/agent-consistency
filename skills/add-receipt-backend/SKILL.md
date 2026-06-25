# Skill: add-receipt-backend

## When to use

Use this when adding or changing receipt storage/export backends.

## Steps

1. Implement the `ReceiptStore` protocol: `add(receipt)` and `list(run_id=None)`.
2. Preserve deduplication by `receipt.key` where the backend can enforce it.
3. Call `receipt.prepare_for_storage(...)` before persistence so digest-chain
   fields are populated.
4. Keep heavyweight dependencies behind optional extras.
5. Add round-trip tests with fakes where live infrastructure is not available.
6. Document retention, rotation, and operational limits.

## Conventions

- Store classes end in `ReceiptStore`.
- Export-only classes end in `ReceiptExporter`.
- Backend configuration is explicit constructor state, not global process state.

## Definition of done

- Round-trip or export tests pass.
- Docs mention the backend and optional extra.
- `docs/STATE.md` records non-obvious tradeoffs.

## Gotchas learned

- Receipt writes should be bufferable and flushable so blocking gate decisions
  can preserve evidence without making every hot-path step wait on remote I/O.

