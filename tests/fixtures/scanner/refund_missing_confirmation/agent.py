def send_email(address, body):
    return {"sent": True, "address": address, "body": body}


def send_refund_confirmation(refund):
    send_email(refund.customer_email, "Your refund is complete.")
