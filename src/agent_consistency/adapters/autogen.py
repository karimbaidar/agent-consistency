from collections.abc import Callable, Mapping
from typing import Any, Optional, TypeVar

from ..integrations import run_gated_step
from ..models import ConsistencyReceipt
from ..run import AgentStep, WorkflowRun
from ..store import ReceiptStore

ResultT = TypeVar("ResultT")


class AutoGenConsistencyAdapter:
    """Dependency-free wrapper for AutoGen-style handlers and reply callbacks."""

    def __init__(
        self,
        run: Optional[WorkflowRun] = None,
        *,
        run_id: Optional[str] = None,
        store: Optional[ReceiptStore] = None,
        on_violation: str = "raise",
    ) -> None:
        self.run = run or WorkflowRun(run_id, store=store, on_violation=on_violation)

    @classmethod
    def detect(
        cls,
        run_id: Optional[str] = None,
        *,
        store: Optional[ReceiptStore] = None,
    ) -> "AutoGenConsistencyAdapter":
        return cls(WorkflowRun.detect(run_id, store=store))

    def wrap_handler(
        self,
        handler_func: Callable[..., ResultT],
        *,
        agent: str,
        action: str,
        step_id: Optional[str] = None,
        metadata: Optional[Mapping[str, Any]] = None,
        pass_step: bool = False,
        outcome_name: Optional[str] = None,
        outcome_check: Optional[Callable[[ResultT], bool]] = None,
    ) -> Callable[..., ResultT]:
        """Wrap an AutoGen tool handler or reply function with a receipt."""

        def wrapped(*args: Any, **kwargs: Any) -> ResultT:
            def handler(step: AgentStep) -> ResultT:
                if pass_step:
                    kwargs_with_step = dict(kwargs)
                    kwargs_with_step["step"] = step
                    return handler_func(*args, **kwargs_with_step)
                return handler_func(*args, **kwargs)

            return run_gated_step(
                self.run,
                agent,
                action,
                handler,
                step_id=step_id or f"{agent}:{action}",
                metadata=metadata,
                outcome_name=outcome_name,
                outcome_check=outcome_check,
            )

        return wrapped

    def wrap_reply(
        self,
        reply_func: Callable[..., ResultT],
        *,
        agent: str,
        step_id: Optional[str] = None,
        metadata: Optional[Mapping[str, Any]] = None,
        pass_step: bool = False,
        outcome_name: Optional[str] = None,
        outcome_check: Optional[Callable[[ResultT], bool]] = None,
    ) -> Callable[..., ResultT]:
        """Wrap an AutoGen reply callback as a customer-visible message step."""
        return self.wrap_handler(
            reply_func,
            agent=agent,
            action="send_customer_message",
            step_id=step_id,
            metadata=metadata,
            pass_step=pass_step,
            outcome_name=outcome_name,
            outcome_check=outcome_check,
        )

    def receipts(self) -> list[ConsistencyReceipt]:
        return self.run.receipts()
