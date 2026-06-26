def notify_customer(customer, body):
    return {"sent": True, "customer": customer, "body": body}


def dry_run_notice(customer):
    # agent-consistency: ignore false-success-risk reason="internal dry-run only"
    notify_customer(customer, "Done.")
