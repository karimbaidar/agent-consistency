from collections.abc import Callable, Mapping
from typing import Any, Optional, TypeVar

from ..integrations import run_gated_step
from ..models import ConsistencyReceipt
from ..run import AgentStep, WorkflowRun
from ..store import ReceiptStore

ResultT = TypeVar("ResultT")


class CrewAIConsistencyAdapter:
    """Dependency-free wrapper for CrewAI-style tools and task callables."""

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
    ) -> "CrewAIConsistencyAdapter":
        return cls(WorkflowRun.detect(run_id, store=store))

    def wrap_tool(
        self,
        tool: Callable[..., ResultT],
        *,
        name: str,
        agent: Optional[str] = None,
        action: Optional[str] = None,
        step_id: Optional[str] = None,
        metadata: Optional[Mapping[str, Any]] = None,
        pass_step: bool = False,
        outcome_name: Optional[str] = None,
        outcome_check: Optional[Callable[[ResultT], bool]] = None,
    ) -> Callable[..., ResultT]:
        """Wrap a CrewAI tool or plain callable with a consistency receipt."""
        return self._wrap_callable(
            tool,
            name=name,
            agent=agent,
            action=action or name,
            step_id=step_id,
            metadata=metadata,
            pass_step=pass_step,
            outcome_name=outcome_name,
            outcome_check=outcome_check,
        )

    def wrap_task(
        self,
        task: Callable[..., ResultT],
        *,
        name: str,
        agent: Optional[str] = None,
        action: Optional[str] = None,
        step_id: Optional[str] = None,
        metadata: Optional[Mapping[str, Any]] = None,
        pass_step: bool = False,
        outcome_name: Optional[str] = None,
        outcome_check: Optional[Callable[[ResultT], bool]] = None,
    ) -> Callable[..., ResultT]:
        """Wrap a CrewAI task callback with a consistency receipt."""
        return self._wrap_callable(
            task,
            name=name,
            agent=agent,
            action=action or f"task:{name}",
            step_id=step_id,
            metadata=metadata,
            pass_step=pass_step,
            outcome_name=outcome_name,
            outcome_check=outcome_check,
        )

    def receipts(self) -> list[ConsistencyReceipt]:
        return self.run.receipts()

    def _wrap_callable(
        self,
        func: Callable[..., ResultT],
        *,
        name: str,
        agent: Optional[str],
        action: str,
        step_id: Optional[str],
        metadata: Optional[Mapping[str, Any]],
        pass_step: bool,
        outcome_name: Optional[str],
        outcome_check: Optional[Callable[[ResultT], bool]],
    ) -> Callable[..., ResultT]:
        def wrapped(*args: Any, **kwargs: Any) -> ResultT:
            def handler(step: AgentStep) -> ResultT:
                if pass_step:
                    kwargs_with_step = dict(kwargs)
                    kwargs_with_step["step"] = step
                    return func(*args, **kwargs_with_step)
                return func(*args, **kwargs)

            return run_gated_step(
                self.run,
                agent or name,
                action,
                handler,
                step_id=step_id or name,
                metadata=metadata,
                outcome_name=outcome_name,
                outcome_check=outcome_check,
            )

        return wrapped
