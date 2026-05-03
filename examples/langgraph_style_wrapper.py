from agent_consistency import WorkflowRun
from agent_consistency.integrations import run_gated_step


def main() -> None:
    run = WorkflowRun("langgraph-style-refund")
    state = {
        "order": {"id": "ord_1", "version": "order-v3", "total": 42.5},
        "refund": {"status": "settled"},
    }

    def refund_node(step):
        order = step.read_state("order", state["order"], version=state["order"]["version"])
        provider_result = {"refund_id": "rf_1", "status": state["refund"]["status"]}
        step.write_state("refund", provider_result, based_on=order, include_value=True)
        return provider_result

    result = run_gated_step(
        run,
        "refund-node",
        "issue_refund",
        refund_node,
        step_id="refund",
        outcome_name="refund_settled",
        outcome_check=lambda refund: refund["status"] == "settled",
    )

    print(result)
    print(run.receipts()[0].to_dict())


if __name__ == "__main__":
    main()
