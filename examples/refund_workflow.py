from agent_consistency import WorkflowRun


def main() -> None:
    run = WorkflowRun("refund-demo")

    with run.step("history-agent", "load_order", step_id="history") as step:
        order = {"id": "ord_1", "previous_refund_count": 0, "total": 42.5}
        order_snapshot = step.read_state("order", order, version="order-v3")
        handoff = step.handoff(
            to_agent="eligibility-agent",
            task="decide refund eligibility",
            facts={"order": order, "policy_version": "policy-v12"},
            evidence={"order.previous_refund_count": order_snapshot.to_dict()},
            required_facts=["order.id", "order.previous_refund_count", "policy_version"],
            required_evidence=["order.previous_refund_count"],
        )

    with run.step("eligibility-agent", "decide", step_id="eligibility") as step:
        policy_snapshot = step.read_state(
            "refund_policy",
            {"max_previous_refunds": 0},
            version="v12",
        )
        step.ensure_fresh(policy_snapshot, current_version="v12")
        step.require_supported_claims(
            handoff,
            {"eligible": True},
            by=["order.previous_refund_count"],
        )
        step.handoff(
            to_agent="refund-agent",
            task="issue refund",
            facts={"order_id": "ord_1", "eligible": True, "amount": 42.5},
            required_facts=["order_id", "eligible", "amount"],
        )

    with run.step("refund-agent", "issue_refund", step_id="refund") as step:
        provider_result = {"refund_id": "rf_1", "status": "settled"}
        step.write_state("refund", provider_result, version="refund-rf_1")
        step.verify_outcome("refund_settled", lambda: provider_result["status"] == "settled")

    for receipt in run.receipts():
        print(receipt.to_dict())


if __name__ == "__main__":
    main()
