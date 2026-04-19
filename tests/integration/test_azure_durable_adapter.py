from agent_consistency.adapters import (
    DurableConsistencyContext,
    durable_instance_id,
    durable_is_replaying,
    replay_safe_log,
    stable_activity_key,
)


class FakeContext:
    def __init__(self):
        self.instance_id = "instance-1"
        self.is_replaying = False
        self.statuses = []

    def set_custom_status(self, payload):
        self.statuses.append(payload)


class FakeLogger:
    def __init__(self):
        self.messages = []

    def info(self, message, *args, **kwargs):
        self.messages.append((message, args, kwargs))


def test_durable_context_uses_instance_id_as_run_id_and_sets_status():
    context = FakeContext()
    durable = DurableConsistencyContext(context)

    with durable.step("agent", "act", step_id="step-1") as step:
        step.read_state("state", {"value": 1}, version="1")

    durable.set_custom_status()

    assert durable_instance_id(context) == "instance-1"
    assert durable.run.run_id == "instance-1"
    assert context.statuses[0]["consistency"]["receipt_count"] == 1


def test_replay_safe_log_skips_replay_messages():
    context = FakeContext()
    logger = FakeLogger()

    replay_safe_log(context, logger, "info", "hello")
    context.is_replaying = True
    replay_safe_log(context, logger, "info", "skip")

    assert durable_is_replaying(context) is True
    assert [message[0] for message in logger.messages] == ["hello"]


def test_stable_activity_key_is_deterministic():
    first = stable_activity_key("instance-1", "refund", {"amount": 10, "order_id": "ord_1"})
    second = stable_activity_key("instance-1", "refund", {"order_id": "ord_1", "amount": 10})

    assert first == second
    assert first.startswith("instance-1:refund:")
