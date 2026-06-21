import json

from agent_consistency import WorkflowRun

run = WorkflowRun("handoff-contract", on_violation="report")

with run.step("history-agent", "handoff_order", step_id="history") as step:
    step.handoff(
        to_agent="refund-agent",
        task="decide refund eligibility",
        facts={"order": {"id": "ord_1"}},
        missing_info=["order.previous_refund_count"],
        required_facts=["order.id", "order.previous_refund_count"],
    )

receipt = run.receipts()[-1]
print(json.dumps(receipt.to_dict(), indent=2))
print("block:", receipt.issues[0].message)
