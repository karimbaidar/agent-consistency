from agent_consistency import WorkflowRun


def main() -> None:
    run = WorkflowRun("tool-outcome-demo", on_violation="record")

    with run.step("refund-agent", "issue_refund", step_id="refund") as step:
        tool_response = {"ok": True, "refund_id": "rf_123", "status": "pending"}
        step.write_state("refund_provider_response", tool_response, include_value=True)
        step.verify_outcome(
            "refund_settled",
            lambda: tool_response["status"] == "settled",
            failure_reason="refund provider did not confirm settlement",
            details=tool_response,
        )

    print(run.receipts()[0].to_dict())


if __name__ == "__main__":
    main()
