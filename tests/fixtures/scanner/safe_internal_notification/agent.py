def notify_internal(message):
    return {"sent": True, "message": message}


def nightly_job():
    notify_internal("Backup complete.")
