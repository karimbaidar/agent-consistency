def _decide(run_id, state, approver):
    return {"run_id": run_id, "state": state, "approver": approver}


def approve_proposal(run_id, approver):
    return _decide(run_id, "approved", approver)
