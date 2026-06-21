import json

from agent_consistency import WorkflowRun

run = WorkflowRun("supported-claims", on_violation="report")

with run.step("comms-agent", "email_customer", step_id="email") as step:
    packet = step.handoff(
        to_agent="comms-agent",
        task="write customer refund email",
        facts={"refund": {"id": "rf_1"}},
    )
    step.require_supported_claims(
        packet,
        {"refund_complete": True},
        by=["refund.status"],
    )

receipt = run.receipts()[-1]
print(json.dumps(receipt.to_dict(), indent=2))
print("block:", receipt.issues[0].message)
