from agent_consistency import detect_risks, render_risk_report
from agent_consistency.adapters import LangGraphConsistencyAdapter


def refund_node(state):
    return {"refund": {"id": "rf_1", "status": state["provider_status"]}}


def main() -> None:
    adapter = LangGraphConsistencyAdapter.detect("langgraph-style-refund")
    refund = adapter.wrap_node(
        refund_node,
        name="refund-node",
        action="issue_refund",
        outcome_name="refund_settled",
        outcome_check=lambda result: result["refund"]["status"] == "settled",
    )

    result = refund({"provider_status": "pending"})
    print(result)
    print(render_risk_report(detect_risks(adapter.receipts())))


if __name__ == "__main__":
    main()
