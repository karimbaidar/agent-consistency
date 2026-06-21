from agent_consistency import WorkflowRun, detect_risks
from agent_consistency.adapters import LangGraphConsistencyAdapter


def test_langgraph_adapter_wraps_node_and_verifies_output():
    adapter = LangGraphConsistencyAdapter.detect("langgraph-risk")

    def refund_node(state):
        return {"refund": {"status": state["provider_status"]}}

    wrapped = adapter.wrap_node(
        refund_node,
        name="refund-node",
        action="issue_refund",
        outcome_name="refund_settled",
        outcome_check=lambda result: result["refund"]["status"] == "settled",
    )

    result = wrapped({"provider_status": "pending"})
    report = detect_risks(adapter.receipts())

    assert result["refund"]["status"] == "pending"
    assert report.has_high_severity is True
    assert adapter.receipts()[0].agent == "refund-node"


def test_langgraph_adapter_can_pass_step_to_node():
    adapter = LangGraphConsistencyAdapter(WorkflowRun("langgraph-step"))

    def policy_node(state, step):
        step.read_state("policy", state["policy"], version=state["policy"]["version"])
        return {"approved": True}

    wrapped = adapter.wrap_node(
        policy_node,
        name="policy-node",
        action="approve_refund",
        pass_step=True,
        outcome_name="approval_recorded",
        outcome_check=lambda result: result["approved"] is True,
    )

    assert wrapped({"policy": {"version": "v1"}}) == {"approved": True}
    assert adapter.receipts()[0].state_reads[0].name == "policy"
