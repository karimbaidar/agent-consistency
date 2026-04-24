import pytest

from agent_consistency import (
    HandoffContract,
    HandoffValidationError,
    VerifierRegistry,
    WorkflowRun,
    build_causality_graph,
    trace_causality,
)


def test_contract_handoff_records_artifacts_and_causality():
    run = WorkflowRun("contract-run")
    contract = HandoffContract.define(
        "refund_approval",
        required_facts=["order_id", "amount"],
        produced_artifacts=["policy_decision"],
    )

    with run.step("policy-agent", "approve", step_id="policy") as step:
        artifact = step.proof_artifact(
            "policy_decision",
            {"eligible": True, "policy_version": "v12"},
            kind="decision",
            verified=True,
            verifier="policy_rule",
        )
        packet = step.handoff(
            to_agent="refund-agent",
            task="issue refund",
            facts={"order_id": "ord_1", "amount": 42.5},
            artifacts=[artifact],
            contract=contract,
        )

    with run.step("refund-agent", "issue", step_id="refund") as step:
        assert step.consume_handoff(packet, contract=contract)

    receipts = run.receipts()
    graph = build_causality_graph(receipts)

    assert receipts[0].produced_handoff_ids == [packet.handoff_id]
    assert receipts[1].consumed_handoff_ids == [packet.handoff_id]
    assert graph.edges
    assert "policy-agent" in trace_causality(receipts)


def test_contract_rejects_unverified_required_artifact():
    run = WorkflowRun("bad-contract")
    contract = HandoffContract.define(
        "refund_approval",
        required_facts=["order_id"],
        produced_artifacts=["policy_decision"],
    )

    with pytest.raises(HandoffValidationError):
        with run.step("policy-agent", "approve", step_id="policy") as step:
            artifact = step.proof_artifact(
                "policy_decision",
                {"eligible": True},
                verified=False,
            )
            step.handoff(
                to_agent="refund-agent",
                task="issue refund",
                facts={"order_id": "ord_1"},
                artifacts=[artifact],
                contract=contract,
            )


def test_dynamic_verifier_registry_can_gate_consumed_handoff():
    registry = VerifierRegistry()

    @registry.register("high_value_refund")
    def high_value_refund(context):
        return context.facts["amount"] < 500

    run = WorkflowRun("dynamic-run")
    contract = HandoffContract.define(
        "refund_execution",
        required_facts=["order_id", "amount"],
        verifier="high_value_refund",
    )

    with run.step("risk-agent", "approve", step_id="risk") as step:
        packet = step.handoff(
            to_agent="refund-agent",
            task="issue refund",
            facts={"order_id": "ord_1", "amount": 42.5},
            contract=contract,
        )

    with run.step("refund-agent", "issue", step_id="refund") as step:
        step.consume_handoff(packet, registry=registry)

    assert run.receipts()[1].outcomes[0].name == "high_value_refund"
    assert run.receipts()[1].outcomes[0].passed is True
