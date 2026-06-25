# Skill: add-framework-adapter

## When to use

Use this when adding a new framework or orchestrator integration.

## Steps

1. Keep the adapter dependency-light: wrap user callables or framework-shaped
   protocols without importing the framework in the base package.
2. Put generic adapters under `src/agent_consistency/adapters/` and named
   product integrations under `src/agent_consistency/integrations/`.
3. Route execution through `WorkflowRun`, `run_gated_step`, `verified_step`, or
   `reliability_gate` so receipts, outcomes, and policy decisions stay uniform.
4. Add deterministic tests with fake framework objects instead of live services.
5. Add a small example that shows the few lines users add to an existing agent.
6. Update docs and `docs/STATE.md` with what is supported now and what remains
   future work.

## Conventions

- Adapter classes end in `ConsistencyAdapter`; native product integrations may
  end in `NativeIntegration` when they expose real framework lifecycle seams.
- Adapter methods should accept a user callable and return a wrapped callable.
- Optional framework packages belong in a named extra in `pyproject.toml`.
- Do not claim a full framework dependency is installed unless tests import it.

## Definition of done

- Adapter test covers pass and blocked/fail-closed behavior.
- Example runs without external services.
- Docs mention dependency expectations and limits.

## Gotchas learned

- Prefer wrapping callables and fake framework contexts. This keeps CI
  deterministic and avoids pulling heavy dependencies into the core install.
- For Microsoft Agent Framework, keep the dependency-light MAF-shaped fallback
  intact and put native async/middleware/streaming seams behind the optional
  `microsoft` extra. Base tests should use fake MAF contexts; real Microsoft
  package tests must be extra-gated.
