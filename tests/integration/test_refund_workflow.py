import pytest

from agent_consistency import OutcomeVerificationError, WorkflowRun


def test_refund_workflow_records_consistent_success():
    run = WorkflowRun("refund-ord-1")
    order = {"id": "ord_1", "total": 42.5, "previous_refund_count": 0}
    policy = {"max_previous_refunds": 0, "max_amount": 100}

    with run.step("history-agent", "load_order", step_id="history") as step:
        order_snapshot = step.read_state("order", order, version="order-v3")
        packet = step.handoff(
            to_agent="eligibility-agent",
            task="decide refund eligibility",
            facts={
                "order": order,
                "policy_version": "policy-v12",
            },
            assumptions=["order data came from the primary order store"],
            constraints=["do not refund if previous_refund_count is greater than zero"],
            evidence={"order.previous_refund_count": order_snapshot.to_dict()},
            required_facts=["order.id", "order.previous_refund_count", "policy_version"],
            required_evidence=["order.previous_refund_count"],
        )

    with run.step("eligibility-agent", "decide", step_id="eligibility") as step:
        policy_snapshot = step.read_state("refund_policy", policy, version="policy-v12")
        step.ensure_fresh(policy_snapshot, current_version="policy-v12")
        step.require_supported_claims(
            packet,
            {"eligible": True},
            by=["order.previous_refund_count"],
        )
        step.handoff(
            to_agent="refund-agent",
            task="issue refund",
            facts={
                "order_id": "ord_1",
                "eligible": True,
                "amount": 42.5,
                "policy_version": "policy-v12",
            },
            required_facts=["order_id", "eligible", "amount", "policy_version"],
        )

    with run.step("refund-agent", "issue_refund", step_id="refund") as step:
        provider_result = {"refund_id": "rf_1", "status": "settled"}
        step.write_state("refund", provider_result, version="refund-rf_1")
        step.verify_outcome(
            "refund_settled",
            lambda: provider_result["status"] == "settled",
            details={"refund_id": "rf_1"},
        )

    assert [receipt.status for receipt in run.receipts()] == ["passed", "passed", "passed"]


def test_refund_workflow_catches_false_success_when_provider_is_pending():
    run = WorkflowRun("refund-pending")

    with pytest.raises(OutcomeVerificationError):
        with run.step("refund-agent", "issue_refund", step_id="refund") as step:
            provider_result = {"refund_id": "rf_2", "status": "pending"}
            step.verify_outcome(
                "refund_settled",
                lambda: provider_result["status"] == "settled",
                failure_reason="refund status is pending, not settled",
                details=provider_result,
            )

    [receipt] = run.receipts()
    assert receipt.status == "failed"
    assert receipt.outcomes[0].details["status"] == "pending"
