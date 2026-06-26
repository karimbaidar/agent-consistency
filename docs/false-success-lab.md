# False Success Lab

The interactive False Success Lab lives in the separate public demo repo:

- Demo: <https://karimbaidar.github.io/false-success-lab/>
- Repo: <https://github.com/karimbaidar/false-success-lab>

This package repo provides the core scanner, report schema, receipt model, and
runtime gates that the demo can call from its backend.

## Scanner Contract

The lab scan entry points should use the same scanner contract as the CLI:

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

## Repo Boundary

Do not add the interactive UI or frontend build pipeline to this package repo.
Keep UI work in `false-success-lab`; keep reusable scanner schema,
package APIs, and docs links here.
