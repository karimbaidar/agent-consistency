from agent_consistency import detect_risks, render_risk_report
from agent_consistency.adapters import AutoGenConsistencyAdapter


def refund_reply(messages, *, step):
    packet = step.handoff(
        to_agent="comms-agent",
        task="write customer message",
        facts={"refund": {"id": "rf_1"}},
    )
    step.require_supported_claims(packet, {"refund_complete": True}, by=["refund.status"])
    return {"reply": "Your refund is complete.", "supported": False}


def main() -> None:
    adapter = AutoGenConsistencyAdapter.detect("autogen-style-refund")
    reply = adapter.wrap_reply(
        refund_reply,
        agent="comms-agent",
        pass_step=True,
        outcome_name="supported_customer_reply",
        outcome_check=lambda result: result["supported"] is True,
    )

    reply([{"role": "user", "content": "Where is my refund?"}])
    print(render_risk_report(detect_risks(adapter.receipts())))


if __name__ == "__main__":
    main()
