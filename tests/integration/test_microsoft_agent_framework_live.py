import asyncio
import importlib
import sys

import pytest

from agent_consistency import OutcomeVerificationError, WorkflowRun
from agent_consistency.integrations import MicrosoftAgentFrameworkNativeIntegration

if sys.version_info >= (3, 10):
    try:
        agent_framework = importlib.import_module("agent_framework")
    except ImportError:
        agent_framework = None
else:
    agent_framework = None

pytestmark = [
    pytest.mark.microsoft_live,
    pytest.mark.skipif(
        sys.version_info < (3, 10),
        reason="agent-framework requires Python 3.10+",
    ),
    pytest.mark.skipif(
        agent_framework is None,
        reason="install agent-consistency[microsoft] to run live Microsoft Agent Framework tests",
    )
]


if agent_framework is not None:

    class DeterministicRefundChatClient(agent_framework.BaseChatClient):
        """Real MAF chat client seam with deterministic local business payloads."""

        def __init__(self, status: str) -> None:
            super().__init__()
            self.status = status
            self.messages_seen = []

        async def _inner_get_response(self, *, messages, stream, options, **kwargs):
            self.messages_seen.append(messages)
            return agent_framework.ChatResponse(
                value={
                    "refund_id": "rf_live",
                    "status": self.status,
                }
            )

else:

    class DeterministicRefundChatClient:
        pass


def test_native_integration_wraps_real_maf_agent_run():
    async def scenario():
        client = DeterministicRefundChatClient("settled")
        agent = agent_framework.Agent(
            client=client,
            name="maf-live-refund-agent",
            instructions="Return the refund provider status.",
        )
        integration = MicrosoftAgentFrameworkNativeIntegration(WorkflowRun("maf-live-pass"))
        wrapped = integration.wrap_agent_run(
            agent,
            action="issue_refund",
            criticality="financial",
            outcome_name="refund_settled",
            result_extractor=lambda response: response.value,
            outcome_check=lambda result: result["status"] == "settled",
        )

        result = await wrapped("issue refund rf_live")

        assert result.value["status"] == "settled"
        assert client.messages_seen
        [receipt] = integration.receipts()
        assert receipt.agent == "maf-live-refund-agent"
        assert receipt.status == "passed"
        assert receipt.outcomes[0].name == "refund_settled"
        assert receipt.outcomes[0].passed is True

    asyncio.run(scenario())


def test_native_integration_fail_closes_real_maf_agent_run():
    async def scenario():
        agent = agent_framework.Agent(
            client=DeterministicRefundChatClient("pending"),
            name="maf-live-refund-agent",
            instructions="Return the refund provider status.",
        )
        integration = MicrosoftAgentFrameworkNativeIntegration(WorkflowRun("maf-live-block"))
        wrapped = integration.wrap_agent_run(
            agent,
            action="issue_refund",
            criticality="financial",
            outcome_name="refund_settled",
            result_extractor=lambda response: response.value,
            outcome_check=lambda result: result["status"] == "settled",
        )

        with pytest.raises(OutcomeVerificationError):
            await wrapped("issue refund rf_live")

        [receipt] = integration.receipts()
        assert receipt.status == "failed"
        assert receipt.outcomes[0].passed is False
        assert receipt.policy_decisions[0]["mode"] == "fail_closed"

    asyncio.run(scenario())
