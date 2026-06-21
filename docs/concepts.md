# Concepts

## False-Success Bugs

A false-success bug happens when an agent reports completion before the real
world agrees. The tool call may have returned. The trace may look green. The
model output may be valid JSON. The business outcome can still be false.

Common forms:

- tool success without outcome success
- stale-state success
- thin-handoff success
- unsupported-claim success
- customer-visible action after an unresolved outcome

## Receipts

Receipts are a flight recorder for AI agents. They are JSON-serializable records
that show what a step read, wrote, handed off, verified, and blocked.

Receipts are useful after the run: CI artifacts, incident reports, audits, and
debugging sessions. They are not a formal proof system.

## Gates

A gate is a runtime check that decides whether continuation is allowed. Gates
can verify state freshness, handoff contracts, proof artifacts, supported
claims, or real-world outcomes.

## Detect Mode

Detect mode records receipts and reports risk without blocking the workflow. It
is the adoption path for teams that want to find false-success bugs before
refactoring their orchestration.

## Verify

`agent-consistency verify` checks receipt structure, references, and digest
chains. It separates integrity from run semantics, so a blocked pending-refund
run can still have verified receipt integrity.
