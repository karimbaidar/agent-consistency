from agent_consistency import detect_risks
from agent_consistency.adapters import AutoGenConsistencyAdapter


def test_autogen_adapter_wraps_handler_and_verifies_output():
    adapter = AutoGenConsistencyAdapter.detect("autogen-risk")

    def send_reply(messages):
        return {"messages": messages, "supported": False}

    wrapped = adapter.wrap_handler(
        send_reply,
        agent="comms-agent",
        action="send_customer_message",
        outcome_name="supported_customer_reply",
        outcome_check=lambda result: result["supported"] is True,
    )

    result = wrapped([{"content": "refund?"}])
    report = detect_risks(adapter.receipts())

    assert result["supported"] is False
    assert report.has_high_severity is True
    assert adapter.receipts()[0].action == "send_customer_message"


def test_autogen_adapter_can_pass_step_to_reply():
    adapter = AutoGenConsistencyAdapter.detect("autogen-step")

    def reply(messages, *, step):
        step.read_state("refund", {"status": "settled"}, version="settled")
        return {"messages": messages, "supported": True}

    wrapped = adapter.wrap_reply(
        reply,
        agent="comms-agent",
        pass_step=True,
        outcome_name="supported_customer_reply",
        outcome_check=lambda result: result["supported"] is True,
    )

    assert wrapped([{"content": "refund?"}])["supported"] is True
    assert adapter.receipts()[0].state_reads[0].name == "refund"
