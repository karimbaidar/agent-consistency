from agent_consistency import detect_risks
from agent_consistency.adapters import CrewAIConsistencyAdapter


def test_crewai_adapter_wraps_tool_and_verifies_output():
    adapter = CrewAIConsistencyAdapter.detect("crewai-risk")

    def issue_refund(order_id):
        return {"order_id": order_id, "status": "pending"}

    wrapped = adapter.wrap_tool(
        issue_refund,
        name="issue-refund",
        outcome_name="refund_settled",
        outcome_check=lambda refund: refund["status"] == "settled",
    )

    refund = wrapped("ord_1")
    report = detect_risks(adapter.receipts())

    assert refund["status"] == "pending"
    assert report.has_high_severity is True
    assert adapter.receipts()[0].agent == "issue-refund"


def test_crewai_adapter_can_pass_step_to_tool():
    adapter = CrewAIConsistencyAdapter.detect("crewai-step")

    def approve_refund(*, step):
        step.read_state("policy", {"version": "v1"}, version="v1")
        return {"approved": True}

    wrapped = adapter.wrap_task(
        approve_refund,
        name="approve-refund",
        pass_step=True,
        outcome_name="approval_recorded",
        outcome_check=lambda result: result["approved"] is True,
    )

    assert wrapped() == {"approved": True}
    assert adapter.receipts()[0].state_reads[0].name == "policy"
