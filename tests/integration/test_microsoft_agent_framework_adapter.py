import pytest

from agent_consistency import OutcomeVerificationError, WorkflowRun, detect_risks
from agent_consistency.integrations import MicrosoftAgentFrameworkConsistencyAdapter


class FakeMafAgent:
    def __init__(self, name, provider_status):
        self.name = name
        self.provider_status = provider_status

    def invoke(self, context):
        return {
            "refund_id": context["refund_id"],
            "status": self.provider_status,
        }


def test_microsoft_adapter_wraps_agent_method_and_reports_risk():
    adapter = MicrosoftAgentFrameworkConsistencyAdapter.detect("maf-risk")
    agent = FakeMafAgent("refund-agent", "pending")

    wrapped = adapter.wrap_agent_method(
        agent,
        method="invoke",
        action="issue_refund",
        outcome_name="refund_settled",
        outcome_check=lambda result: result["status"] == "settled",
    )

    result = wrapped({"refund_id": "rf_1"})
    report = detect_risks(adapter.receipts())

    assert result["status"] == "pending"
    assert report.has_high_severity is True
    assert adapter.receipts()[0].agent == "refund-agent"


def test_microsoft_adapter_fail_closed_blocks_side_effect_claim():
    adapter = MicrosoftAgentFrameworkConsistencyAdapter(WorkflowRun("maf-block"))
    agent = FakeMafAgent("refund-agent", "pending")

    wrapped = adapter.wrap_agent_method(
        agent,
        method="invoke",
        action="issue_refund",
        criticality="financial",
        outcome_name="refund_settled",
        outcome_check=lambda result: result["status"] == "settled",
    )

    with pytest.raises(OutcomeVerificationError):
        wrapped({"refund_id": "rf_1"})

    [receipt] = adapter.receipts()
    assert receipt.status == "failed"
    assert receipt.policy_decisions[0]["mode"] == "fail_closed"


def test_microsoft_adapter_can_pass_step_and_record_state():
    adapter = MicrosoftAgentFrameworkConsistencyAdapter(WorkflowRun("maf-step"))

    def invoke(context, *, step):
        step.read_state("order", context["order"], version=context["order"]["version"])
        return {"ok": True}

    wrapped = adapter.wrap_callable(
        invoke,
        agent="order-agent",
        action="load_order",
        pass_step=True,
        outcome_name="order_loaded",
        outcome_check=lambda result: result["ok"] is True,
    )

    assert wrapped({"order": {"id": "ord_1", "version": "order-v1"}}) == {"ok": True}
    [receipt] = adapter.receipts()
    assert receipt.state_reads[0].name == "order"


def test_microsoft_adapter_records_handoff_contract():
    adapter = MicrosoftAgentFrameworkConsistencyAdapter(WorkflowRun("maf-handoff"))

    packet = adapter.record_handoff(
        from_agent="intake-agent",
        to_agent="refund-agent",
        task="issue refund",
        facts={"order_id": "ord_1", "amount": 42.5},
        required_facts=["order_id", "amount"],
    )

    assert packet.to_agent == "refund-agent"
    [receipt] = adapter.receipts()
    assert receipt.handoffs[0].facts["amount"] == 42.5

