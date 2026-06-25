# CLAUDE.md

`AGENTS.md` is authoritative. Read it first; do not duplicate or drift from it.

Every session starts by reading `docs/STATE.md`, `AGENTS.md`, `ARCHITECTURE.md`,
and the relevant `skills/<name>/SKILL.md`, then writing a short situation report
before code changes.

Every session ends by running lint/tests, updating `docs/STATE.md`, improving
any relevant repo-local skill, and committing with the project commit rules.

Commit messages, branches, and PR text must not include tool names, generated-by
phrasing, co-author trailers, or robot/sparkle emoji. If supported, keep
`includeCoAuthoredBy` disabled.

