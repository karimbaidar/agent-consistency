# Skill: write-outcome-verifier

## When to use

Use this when adding an outcome check for a business-visible side effect.

## Steps

1. Name the outcome in business terms, such as `refund_settled` or
   `ticket_created`.
2. Query the authoritative source of truth, not the model response.
3. Return an `OutcomeResult` with a clear pass/fail reason and useful details.
4. Attach the verifier through `step.verify_outcome(...)`, `verify_with(...)`,
   `reliability_gate(...)`, or `verified_step(...)`.
5. Add tests for pass, fail, and provider-error behavior.
6. Document what is checked and what is not checked.

## Conventions

- Verifier class names end in `OutcomeVerifier`.
- Failure reasons should name the source of truth that did not confirm the
  outcome.
- Do not call a model to decide whether the model was right.

## Definition of done

- Ground-truth pass and fail tests exist.
- Provider errors resolve through fail-open / fail-closed policy when used in a
  gated action.
- Docs and `ARCHITECTURE.md` stay honest about evidence limits.

## Gotchas learned

- A successful tool response is evidence, not the outcome itself.
- Provider errors should be converted into failed `OutcomeResult` records when
  possible so fail-open / fail-closed policy can decide continuation.
