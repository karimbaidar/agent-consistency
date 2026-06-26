# False Success Lab

Subtitle:

> Scan your agent repo, find false-success risks, then watch the gate block them.

First-screen options:

1. Try a built-in false-success scenario
2. Scan your own repo
3. Scan a public GitHub repo

The scan entry points should call the same scanner as the CLI:

```bash
agent-consistency scan .
agent-consistency scan https://github.com/org/repo
```

The report card should surface:

```text
False-success report card

Risky actions found: 7
High severity: 3
False-success exposure: 7 unguarded actions

Top finding:
send_refund_confirmation may claim completion before refund settlement is confirmed.
```

The scanner must stay honest. Low-confidence findings should say:

```text
Possible risk, needs review.
```

The **Copy report** button should copy the Markdown output from:

```bash
agent-consistency scan . --format markdown
```

That Markdown is designed for GitHub issues, PR comments, and social posts.
