from agent_consistency import WorkflowRun


def main() -> None:
    run = WorkflowRun("stale-state-demo", on_violation="record")

    with run.step("policy-agent", "evaluate_refund", step_id="policy") as step:
        policy = {"version": "policy-v12", "max_refund_amount": 100}
        snapshot = step.read_state("refund_policy", policy, version=policy["version"])
        step.ensure_fresh(snapshot, current_version="policy-v14")
        step.write_state("policy_decision", {"eligible": True}, based_on=snapshot)

    print(run.receipts()[0].to_dict())


if __name__ == "__main__":
    main()
