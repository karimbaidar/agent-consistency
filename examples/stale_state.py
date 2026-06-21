import json

from agent_consistency import WorkflowRun

run = WorkflowRun("stale-state", on_violation="report")
policy_v12 = {"max_refund": 100}

with run.step("policy-agent", "approve_refund", step_id="policy") as step:
    policy = step.read_state("refund_policy", policy_v12, version="v12")
    step.ensure_fresh(policy, current_value={"max_refund": 50}, current_version="v14")

receipt = run.receipts()[-1]
print(json.dumps(receipt.to_dict(), indent=2))
print("block:", receipt.issues[0].message)
