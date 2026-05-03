from agent_consistency import HandoffContract, WorkflowRun


def main() -> None:
    run = WorkflowRun("approval-gate-demo")
    approval_contract = HandoffContract.define(
        "human_approval_gate",
        required_facts=["request_id", "amount", "approved_by"],
        produced_artifacts=["approval_record"],
    )

    with run.step("approval-agent", "request_human_approval", step_id="approval") as step:
        approval = {"request_id": "refund-1", "amount": 640, "approved_by": "ops-lead"}
        artifact = step.proof_artifact(
            "approval_record",
            approval,
            kind="approval",
            verified=True,
            verifier="human_review",
        )
        packet = step.handoff(
            to_agent="refund-agent",
            task="issue high-risk refund",
            facts=approval,
            artifacts=[artifact],
            contract=approval_contract,
        )

    with run.step("refund-agent", "issue_refund", step_id="refund") as step:
        step.consume_handoff(packet, contract=approval_contract)
        step.verify_outcome("approval_present", lambda: packet.facts["approved_by"] == "ops-lead")

    for receipt in run.receipts():
        print(receipt.to_dict())


if __name__ == "__main__":
    main()
