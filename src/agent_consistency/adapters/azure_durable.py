from collections.abc import Mapping
from typing import Any, Optional

from ..models import ConsistencyReceipt
from ..run import WorkflowRun
from ..serialization import stable_digest, to_jsonable
from ..store import ReceiptStore


def _get_attr(context: Any, *names: str) -> Any:
    for name in names:
        if hasattr(context, name):
            value = getattr(context, name)
            return value() if callable(value) else value
        if isinstance(context, Mapping) and name in context:
            return context[name]
    return None


def durable_instance_id(context: Any) -> str:
    value = _get_attr(context, "instance_id", "instanceId", "instanceID")
    return str(value or "durable-instance-unknown")


def durable_is_replaying(context: Any) -> bool:
    value = _get_attr(context, "is_replaying", "isReplaying")
    return bool(value)


def replay_safe_log(
    context: Any,
    logger: Any,
    level: str,
    message: str,
    *args: Any,
    **kwargs: Any,
) -> None:
    if durable_is_replaying(context):
        return
    log_method = getattr(logger, level)
    log_method(message, *args, **kwargs)


def stable_activity_key(instance_id: str, activity_name: str, intent: Mapping[str, Any]) -> str:
    digest = stable_digest(
        {
            "instance_id": instance_id,
            "activity_name": activity_name,
            "intent": to_jsonable(intent),
        }
    )
    return f"{instance_id}:{activity_name}:{digest[:16]}"


class DurableConsistencyContext:
    def __init__(
        self,
        context: Any,
        *,
        store: Optional[ReceiptStore] = None,
        on_violation: str = "raise",
    ) -> None:
        self.context = context
        self.run = WorkflowRun(
            durable_instance_id(context),
            store=store,
            on_violation=on_violation,
        )

    @property
    def is_replaying(self) -> bool:
        return durable_is_replaying(self.context)

    @property
    def instance_id(self) -> str:
        return durable_instance_id(self.context)

    def step(self, *args: Any, **kwargs: Any) -> Any:
        return self.run.step(*args, **kwargs)

    def activity_key(self, activity_name: str, intent: Mapping[str, Any]) -> str:
        return stable_activity_key(self.instance_id, activity_name, intent)

    def set_custom_status(self, receipt: Optional[ConsistencyReceipt] = None) -> None:
        setter = getattr(self.context, "set_custom_status", None) or getattr(
            self.context,
            "setCustomStatus",
            None,
        )
        if setter is None:
            return
        if receipt is None:
            receipts = self.run.receipts()
            payload = {
                "consistency": {
                    "run_id": self.run.run_id,
                    "receipt_count": len(receipts),
                    "last_status": receipts[-1].status if receipts else "empty",
                }
            }
        else:
            payload = {"consistency": receipt.to_dict()}
        setter(payload)
