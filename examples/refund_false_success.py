import json

from agent_consistency import WorkflowRun

run = WorkflowRun("refund-false-success", on_violation="report")
refund = {"refund_id": "rf_1", "status": "pending"}

with run.step("refund-agent", "issue_refund", step_id="refund") as step:
    step.write_state("refund", refund, include_value=True)
    step.verify_outcome(
        "refund_settled",
        lambda: refund["status"] == "settled",
        failure_reason="payment provider says pending",
        details=refund,
    )

receipt = run.receipts()[-1]
print(json.dumps(receipt.to_dict(), indent=2))
print("block:", receipt.issues[0].message)
