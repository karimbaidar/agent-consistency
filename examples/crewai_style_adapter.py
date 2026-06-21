from agent_consistency import detect_risks, render_risk_report
from agent_consistency.adapters import CrewAIConsistencyAdapter


def issue_refund(order_id, *, step):
    refund = {"order_id": order_id, "status": "pending"}
    step.write_state("refund", refund, include_value=True)
    return refund


def main() -> None:
    adapter = CrewAIConsistencyAdapter.detect("crewai-style-refund")
    refund_tool = adapter.wrap_tool(
        issue_refund,
        name="issue-refund",
        pass_step=True,
        outcome_name="refund_settled",
        outcome_check=lambda refund: refund["status"] == "settled",
    )

    refund_tool("ord_1")
    print(render_risk_report(detect_risks(adapter.receipts())))


if __name__ == "__main__":
    main()
