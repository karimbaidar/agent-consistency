# CLI

## `report`

Summarize receipts:

```bash
agent-consistency report runs/demo/receipts.jsonl
agent-consistency report runs/demo --html runs/demo/report.html
```

## `detect`

Report false-success risk:

```bash
agent-consistency detect runs/demo/receipts.jsonl
```

The command exits non-zero when it finds high-severity risk. That makes it a CI
check for missing gates, stale reads, dropped handoff facts, failed outcomes,
and customer-visible action after unresolved outcomes.

## `verify`

Verify receipt structure and digest chains:

```bash
agent-consistency verify runs/demo/receipts.jsonl
```

`verify` distinguishes receipt integrity from run status.

## `schema`

Print the packaged receipt schema:

```bash
agent-consistency schema
```
