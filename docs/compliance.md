# Compliance Framing

`agent-consistency` creates evidence for agent workflow decisions. It does not
make a system compliant by itself, and this document is not legal advice.

The practical value is record keeping: receipts make specific workflow claims
inspectable after the run.

## What Receipts Can Show

A receipt can show:

- which agent step ran
- which state snapshots were read
- which handoff facts and evidence were attached
- which proof artifacts were referenced
- which outcomes were checked
- whether a gate passed or failed
- which issue blocked continuation
- whether a JSONL receipt chain verifies after storage

That evidence can support incident review, audit preparation, model risk
management, and human oversight workflows.

The JSONL chain is tamper-evident through receipt digests. It is not signed and
is not tamper-proof. Use trusted storage, access control, and future signing
work if your compliance process needs authorship or non-repudiation guarantees.

## What Receipts Do Not Prove

Receipts are not a formal proof of global correctness. They do not prove that:

- the model was truthful in every statement
- every relevant external system was checked
- the business process satisfies a law or regulation
- provider logs, database records, or human approvals are complete

They document the checks the workflow actually declared and performed.

## Mapping To Oversight

For customer-visible or business-critical workflows, receipts can map onto
common oversight questions:

| Oversight question | Receipt evidence |
| --- | --- |
| What did the agent rely on? | State reads, handoff facts, proof artifacts |
| Was the source of truth checked? | Outcome results and failure reasons |
| Why was continuation blocked? | Issues, failed outcomes, receipt status |
| Can the record be inspected later? | JSONL receipts and digest-chain verification |
| Was a human gate involved? | Workflow-specific state, handoff, or approval evidence recorded in the receipt |

If your process needs human approval, model governance review, retention rules,
or regulator-specific controls, implement those controls around the workflow and
record the relevant evidence in receipts.

## Human Approval Gate

A human approval gate is an oversight control owned by the workflow, not magic
inside the package. `agent-consistency` can record that the gate happened by
capturing required handoff facts such as `approved_by`, attaching a verified
approval artifact, and blocking the downstream action when those facts or
artifacts are missing.

The `examples/approval_gate.py` example shows this pattern with a handoff
contract and verified approval artifact. In a regulated workflow, the same
receipt trail can map onto human oversight and record-keeping obligations, but
the surrounding approval policy, retention policy, and reviewer authority still
belong to the deployer.

## EU AI Act Style Language

Use careful wording. Receipts can map onto record-keeping, transparency, and
human oversight needs because they preserve workflow evidence. They do not, by
themselves, certify compliance with the EU AI Act or any other law.

Good wording:

> Receipts provide inspectable evidence that can support record-keeping and
> oversight processes.

Avoid wording:

> This makes the agent compliant.
