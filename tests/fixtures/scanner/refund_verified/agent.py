from agent_consistency import reliability_gate


def send_email(address, body):
    return {"sent": True, "address": address, "body": body}


def send_refund_confirmation(refund, run):
    with reliability_gate(run, "comms-agent", "send_refund_confirmation") as gate:
        gate.step.verify_outcome(
            "refund_settled",
            lambda: refund.status == "settled",
        )
        send_email(refund.customer_email, "Your refund is complete.")
