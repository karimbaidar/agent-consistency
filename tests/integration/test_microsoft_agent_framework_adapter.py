import asyncio

import pytest

from agent_consistency import OutcomeVerificationError, WorkflowRun, detect_risks
from agent_consistency.integrations import (
    MicrosoftAgentFrameworkConsistencyAdapter,
    MicrosoftAgentFrameworkNativeIntegration,
)


class FakeMafAgent:
    def __init__(self, name, provider_status):
        self.name = name
        self.provider_status = provider_status

    def invoke(self, context):
        return {
            "refund_id": context["refund_id"],
            "status": self.provider_status,
        }


class FakeNativeMafAgent:
    name = "native-refund-agent"

    def __init__(self, provider_status):
        self.provider_status = provider_status

    async def run(self, context):
        return {
            "refund_id": context["refund_id"],
            "status": self.provider_status,
        }

    async def run_stream(self, context):
        yield {"event": "tool_result", "refund_id": context["refund_id"]}
        yield {"refund_id": context["refund_id"], "status": self.provider_status}


class FakeMafFunction:
    name = "issue_refund"


class FakeMafContext:
    def __init__(self, *, run_id="maf-native", invocation_id="invoke-1"):
        self.run_id = run_id
        self.session_id = run_id
        self.invocation_id = invocation_id
        self.function = FakeMafFunction()
        self.metadata = {"policy_version": "v14"}
        self.result = None


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


def test_native_microsoft_wraps_async_agent_run_and_blocks():
    async def scenario():
        adapter = MicrosoftAgentFrameworkNativeIntegration(WorkflowRun("maf-native-run"))
        agent = FakeNativeMafAgent("pending")
        wrapped = adapter.wrap_agent_run(
            agent,
            action="issue_refund",
            criticality="financial",
            outcome_name="refund_settled",
            outcome_check=lambda result: result["status"] == "settled",
        )

        with pytest.raises(OutcomeVerificationError):
            await wrapped({"refund_id": "rf_1"})

        [receipt] = adapter.receipts()
        assert receipt.agent == "native-refund-agent"
        assert receipt.status == "failed"
        assert receipt.policy_decisions[0]["mode"] == "fail_closed"

    asyncio.run(scenario())


def test_native_microsoft_agent_middleware_maps_context_and_result():
    async def scenario():
        adapter = MicrosoftAgentFrameworkNativeIntegration()
        context = FakeMafContext(run_id="maf-context-run", invocation_id="agent-call-1")
        middleware = adapter.agent_middleware(
            agent="refund-agent",
            action="issue_refund",
            criticality="financial",
            outcome_name="refund_settled",
            outcome_check=lambda result: result["status"] == "settled",
        )

        async def call_next():
            context.result = {"refund_id": "rf_1", "status": "settled"}

        await middleware(context, call_next)

        [receipt] = adapter.receipts(run_id="maf-context-run")
        assert receipt.step_id == "agent-call-1"
        assert receipt.status == "passed"
        assert receipt.metadata["invocation_id"] == "agent-call-1"
        assert receipt.metadata["metadata"]["policy_version"] == "v14"

    asyncio.run(scenario())


def test_native_microsoft_function_middleware_records_tool_result():
    async def scenario():
        adapter = MicrosoftAgentFrameworkNativeIntegration(WorkflowRun("maf-function-run"))
        context = FakeMafContext(invocation_id="tool-call-1")
        middleware = adapter.function_middleware(
            agent="refund-tool",
            criticality="financial",
            idempotency_key=lambda ctx: f"refund:{ctx.invocation_id}",
            outcome_name="refund_settled",
            outcome_check=lambda result: result["status"] == "settled",
        )

        async def call_next():
            context.result = {"refund_id": "rf_1", "status": "settled"}

        await middleware(context, call_next)

        [receipt] = adapter.receipts()
        assert receipt.action == "issue_refund"
        assert receipt.idempotency_key == "refund:tool-call-1"
        assert receipt.status == "passed"

    asyncio.run(scenario())


def test_native_microsoft_streaming_wrap_verifies_after_chunks():
    async def scenario():
        adapter = MicrosoftAgentFrameworkNativeIntegration(WorkflowRun("maf-stream-run"))
        agent = FakeNativeMafAgent("pending")
        wrapped = adapter.wrap_agent_stream(
            agent,
            action="issue_refund_stream",
            criticality="financial",
            outcome_name="refund_settled",
            outcome_check=lambda result: result["status"] == "settled",
            stream_result_reducer=lambda chunks: chunks[-1],
        )
        chunks = []

        with pytest.raises(OutcomeVerificationError):
            async for chunk in wrapped({"refund_id": "rf_1"}):
                chunks.append(chunk)

        assert chunks[0]["event"] == "tool_result"
        [receipt] = adapter.receipts()
        assert receipt.status == "failed"
        assert receipt.outcomes[0].name == "refund_settled"

    asyncio.run(scenario())
