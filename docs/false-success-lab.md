# False Success Lab

Subtitle:

> Scan your agent repo, find false-success risks, then watch the gate block them.

Start the local lab:

```bash
agent-consistency lab
```

Open `http://127.0.0.1:8765`.

The lab is a packaged Svelte UI served by the Python package. It calls the same
scanner as the CLI, so the report card matches `agent-consistency scan`.

First-screen options:

1. Try a built-in false-success scenario
2. Scan your own repo
3. Scan a public GitHub repo

The scan entry points call:

```bash
agent-consistency scan .
agent-consistency scan https://github.com/org/repo
```

The report card surfaces:

```text
False-success report card

Risky actions found: 7
High severity: 3
False-success exposure: 7 unguarded actions

Top finding:
send_refund_confirmation may claim completion before refund settlement is confirmed.
```

The scanner stays honest. Low-confidence findings say:

```text
Possible risk, needs review.
```

The **Copy report** button copies the Markdown output from:

```bash
agent-consistency scan . --format markdown
```

That Markdown is designed for GitHub issues, PR comments, and social posts.

The gate display is derived from the scan:

- `BLOCK` when high-severity exposure is found.
- `REVIEW` when lower-severity exposure is found.
- `ALLOW` when no configured static finding fired.

`ALLOW` is not a proof of safety. The UI keeps that caveat visible because a
static scan cannot replace runtime outcome gates.
