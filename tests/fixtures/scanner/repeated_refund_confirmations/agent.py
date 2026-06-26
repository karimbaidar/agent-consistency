def send_email(address, body):
    return {"sent": True, "address": address, "body": body}


def confirm_first_refund(refund):
    send_email(refund.customer_email, "Your refund is complete.")


def confirm_second_refund(refund):
    send_email(refund.customer_email, "Your refund is complete.")
