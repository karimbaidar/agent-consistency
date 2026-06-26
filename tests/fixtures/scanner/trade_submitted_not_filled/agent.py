def send_message(address, body):
    return {"sent": True, "address": address, "body": body}


def place_trade(broker, order, customer):
    broker.submit_order(order)
    send_message(customer.email, "Order filled.")
