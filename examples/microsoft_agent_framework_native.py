"""Native Microsoft Agent Framework integration sketch.

Requires:
    python -m pip install "agent-consistency[microsoft]"

This file intentionally keeps Microsoft imports inside functions so the example
can live in the repository without making CI install external providers.
"""

from agent_consistency.integrations import MicrosoftAgentFrameworkNativeIntegration


def build_refund_agent(provider_lookup):
    from agent_framework import Agent
    from agent_framework.openai import OpenAIChatClient

    integration = MicrosoftAgentFrameworkNativeIntegration(run_id="maf-refund-demo")

    consistency_middleware = integration.agent_middleware(
        agent="refund-agent",
        action="issue_refund",
        criticality="financial",
        outcome_name="refund_settled",
        result_extractor=lambda context: provider_lookup(context.result["refund_id"]),
        outcome_check=lambda refund: refund["status"] == "settled",
    )

    return Agent(
        client=OpenAIChatClient(),
        name="RefundAgent",
        instructions="Issue refunds only when provider settlement can be verified.",
        middleware=[consistency_middleware],
    )
