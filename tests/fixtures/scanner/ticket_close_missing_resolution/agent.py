def notify_customer(customer, body):
    return {"sent": True, "customer": customer, "body": body}


def close_ticket(ticket):
    ticket.status = "resolved"
    notify_customer(ticket.customer, "Ticket closed.")
