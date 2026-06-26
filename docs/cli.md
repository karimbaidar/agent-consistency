# CLI

## `scan`

Scan source code for false-success risk before runtime integration:

```bash
agent-consistency scan .
agent-consistency scan . --format json
agent-consistency scan . --format markdown
agent-consistency scan . --fail-on high
agent-consistency scan . --write-baseline
agent-consistency scan . --baseline agent-consistency-baseline.json
agent-consistency scan https://github.com/org/repo
```

The scanner looks for risky customer-visible, financial, destructive,
access-control, trading, support, and production-state actions that do not have
nearby outcome confirmation. It is intentionally conservative: weak findings are
reported as `Possible risk, needs review.` rather than certain bugs.

Use suppression comments for reviewed false positives:

```python
# agent-consistency: ignore false-success-risk reason="internal dry-run only"
notify_customer(customer, "Done.")
```

Use `--format markdown` for the same clean report payload a lab or UI can expose
through a **Copy report** button.

## `lab`

Start the local False Success Lab UI:

```bash
agent-consistency lab
```

The lab serves a packaged Svelte app at `http://127.0.0.1:8765` and uses the
same scanner as the CLI. The first screen offers:

1. Try a built-in false-success scenario
2. Scan your own repo
3. Scan a public GitHub repo

Use `--host` and `--port` when the default bind address is already occupied:

```bash
agent-consistency lab --host 127.0.0.1 --port 8787
```

The **Copy report** button copies the Markdown report returned by the scanner,
so the output is ready for GitHub issues, PR comments, or social posts.

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
