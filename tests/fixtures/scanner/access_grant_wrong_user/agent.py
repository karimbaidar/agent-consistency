def assign_role(user_id, role):
    return {"user_id": user_id, "role": role}


def send_message(address, body):
    return {"sent": True, "address": address, "body": body}


def grant_access(user, role):
    assign_role(user.id, role)
    send_message(user.email, "Access granted.")
