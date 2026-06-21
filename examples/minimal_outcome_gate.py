import json

from agent_consistency import WorkflowRun

run = WorkflowRun("minimal-outcome-gate", on_violation="report")
provider_result = {"ticket_id": "t_1", "status": "queued"}

with run.step("ticket-agent", "close_ticket", step_id="close-ticket") as step:
    step.verify_outcome(
        "ticket_closed",
        lambda: provider_result["status"] == "closed",
        failure_reason="ticket system still reports queued",
        details=provider_result,
    )

receipt = run.receipts()[-1]
print(json.dumps(receipt.to_dict(), indent=2))
print("block:", receipt.issues[0].message)
