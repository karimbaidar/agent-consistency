import pytest

from agent_consistency import HandoffValidationError, WorkflowRun


def test_handoff_validates_required_nested_facts():
    run = WorkflowRun("handoff-run")

    with run.step("history-agent", "load_order", step_id="history") as step:
        packet = step.handoff(
            to_agent="eligibility-agent",
            task="decide refund eligibility",
            facts={"order": {"id": "ord_1", "previous_refund_count": 0}},
            required_facts=["order.id", "order.previous_refund_count"],
        )

    assert packet.facts["order"]["previous_refund_count"] == 0
    assert run.receipts()[0].status == "passed"


def test_handoff_fails_when_required_fact_is_missing():
    run = WorkflowRun("handoff-missing")

    with pytest.raises(HandoffValidationError):
        with run.step("history-agent", "load_order", step_id="history") as step:
            step.handoff(
                to_agent="eligibility-agent",
                task="decide refund eligibility",
                facts={"order": {"id": "ord_1"}},
                missing_info=["order.previous_refund_count"],
                required_facts=["order.previous_refund_count"],
            )

    [receipt] = run.receipts()
    assert receipt.status == "failed"
    assert receipt.handoffs[0].missing_info == ["order.previous_refund_count"]
    assert receipt.issues[0].code == "invalid_handoff"


def test_downstream_claims_must_be_supported_by_facts_or_evidence():
    run = WorkflowRun("claim-run")

    with pytest.raises(HandoffValidationError):
        with run.step("writer-agent", "email_customer", step_id="writer") as step:
            packet = step.handoff(
                to_agent="writer-agent",
                task="write customer email",
                facts={"refund": {"id": "rf_1"}},
            )
            step.require_supported_claims(
                packet,
                {"refund_complete": True},
                by=["refund.status"],
            )

    [receipt] = run.receipts()
    assert receipt.issues[0].code == "unsupported_claim"
