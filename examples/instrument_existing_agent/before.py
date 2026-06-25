class RefundAgent:
    def __init__(self, provider_status):
        self.provider_status = provider_status

    def issue_refund(self, order_id):
        refund = {"refund_id": f"rf_{order_id}", "status": self.provider_status}
        return {
            "refund": refund,
            "customer_message": "your refund is complete",
        }


def run_demo(provider_status="pending"):
    agent = RefundAgent(provider_status)
    return agent.issue_refund("ord_1")


if __name__ == "__main__":
    print(run_demo())

