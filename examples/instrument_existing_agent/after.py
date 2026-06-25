from agent_consistency import RefundSettlementVerifier, WorkflowRun, verified_step


class RefundAgent:
    def __init__(self, provider_status):
        self.provider_status = provider_status

    def provider_lookup(self, refund_id):
        return {"refund_id": refund_id, "status": self.provider_status}

    def issue_refund(self, order_id):
        refund = {"refund_id": f"rf_{order_id}", "status": self.provider_status}
        return {
            "refund": refund,
            "customer_message": "your refund is complete",
        }


def instrument(agent, run):
    agent.issue_refund = verified_step(
        run,
        "refund-agent",
        "issue_refund",
        criticality="financial",
        outcome_verifier=lambda result: RefundSettlementVerifier(
            result["refund"]["refund_id"],
            agent.provider_lookup,
        ),
    )(agent.issue_refund)
    return agent


def run_demo(provider_status="settled"):
    run = WorkflowRun("instrument-existing-agent")
    agent = instrument(RefundAgent(provider_status), run)
    result = agent.issue_refund("ord_1")
    return result, run.receipts()


if __name__ == "__main__":
    result, receipts = run_demo()
    print(result)
    print(receipts[-1].status)

