import pytest

from agent_consistency import (
    HandoffValidationError,
    OutcomeVerificationError,
    RefundSettlementVerifier,
    WorkflowRun,
    reliability_gate,
    verified_step,
)


class FakeSpan:
    def __init__(self, attributes):
        self.attributes = dict(attributes)

    def set_attribute(self, key, value):
        self.attributes[key] = value


class FakeSpanContext:
    def __init__(self, span):
        self.span = span

    def __enter__(self):
        return self.span

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeTracer:
    def __init__(self):
        self.spans = []

    def start_as_current_span(self, name, attributes):
        span = FakeSpan({"span.name": name, **attributes})
        self.spans.append(span)
        return FakeSpanContext(span)


def test_reliability_gate_records_state_handoff_outcome_and_decision():
    run = WorkflowRun("api-gate-run")
    provider = {"rf_1": {"status": "settled"}}

    with reliability_gate(
        run,
        "refund-agent",
        "issue_refund",
        step_id="refund",
        criticality="financial",
        state_name="refund_policy",
        state_value={"max_amount": 100},
        state_version="policy-v1",
        current_version="policy-v1",
        handoff_facts={"order_id": "ord_1", "amount": 42.5},
        required_handoff_facts=["order_id", "amount"],
        outcome_verifier=RefundSettlementVerifier("rf_1", provider.__getitem__),
    ) as gate:
        gate.step.write_state("refund", {"refund_id": "rf_1", "status": "settled"})

    assert gate.decision.allowed is True
    [receipt] = run.receipts()
    assert receipt.status == "passed"
    assert receipt.state_reads[0].name == "refund_policy"
    assert receipt.handoffs[0].facts["order_id"] == "ord_1"
    assert receipt.outcomes[0].passed is True


def test_reliability_gate_blocks_missing_required_facts():
    run = WorkflowRun("missing-facts-run")

    with pytest.raises(HandoffValidationError):
        with reliability_gate(
            run,
            "refund-agent",
            "issue_refund",
            step_id="refund",
            handoff_facts={"order_id": "ord_1"},
            required_handoff_facts=["order_id", "amount"],
        ):
            pass

    [receipt] = run.receipts()
    assert receipt.status == "failed"
    assert receipt.issues[0].code == "invalid_handoff"


def test_verified_step_decorator_wraps_plain_callable():
    run = WorkflowRun("decorator-run")

    def verifier_for(result):
        return RefundSettlementVerifier(
            result["refund_id"],
            lambda refund_id: {"refund_id": refund_id, "status": result["status"]},
        )

    @verified_step(
        run,
        "refund-agent",
        "issue_refund",
        step_id="refund",
        criticality="financial",
        outcome_verifier=verifier_for,
    )
    def issue_refund():
        return {"refund_id": "rf_1", "status": "settled"}

    assert issue_refund()["refund_id"] == "rf_1"
    [receipt] = run.receipts()
    assert receipt.status == "passed"
    assert receipt.outcomes[0].name == "refund_settled"


def test_verified_step_decorator_blocks_failed_outcome():
    run = WorkflowRun("decorator-block-run")

    @verified_step(
        run,
        "refund-agent",
        "issue_refund",
        step_id="refund",
        criticality="financial",
        outcome_verifier=lambda result: RefundSettlementVerifier(
            result["refund_id"],
            lambda refund_id: {"refund_id": refund_id, "status": "pending"},
        ),
    )
    def issue_refund():
        return {"refund_id": "rf_1"}

    with pytest.raises(OutcomeVerificationError):
        issue_refund()

    [receipt] = run.receipts()
    assert receipt.status == "failed"
    assert receipt.policy_decisions[0]["mode"] == "fail_closed"


def test_reliability_gate_emits_otel_attributes_with_injected_tracer():
    tracer = FakeTracer()
    run = WorkflowRun("otel-run")

    with reliability_gate(
        run,
        "agent",
        "act",
        step_id="step-1",
        criticality="low",
        tracer=tracer,
    ):
        pass

    [span] = tracer.spans
    assert span.attributes["gen_ai.operation.name"] == "act"
    assert span.attributes["gen_ai.system"] == "agent-consistency"
    assert span.attributes["agent_consistency.run_id"] == "otel-run"
    assert span.attributes["agent_consistency.step_id"] == "step-1"
    assert span.attributes["agent_consistency.status"] == "passed"

