from collections.abc import Callable, Mapping
from typing import Any, Optional, TypeVar

from ..integrations import run_gated_step
from ..models import ConsistencyReceipt
from ..run import AgentStep, WorkflowRun
from ..store import ReceiptStore

StateT = TypeVar("StateT")
ResultT = TypeVar("ResultT")


class LangGraphConsistencyAdapter:
    """Dependency-free wrapper for LangGraph-style node callables."""

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
    ) -> "LangGraphConsistencyAdapter":
        return cls(WorkflowRun.detect(run_id, store=store))

    def wrap_node(
        self,
        node: Callable[..., ResultT],
        *,
        name: str,
        agent: Optional[str] = None,
        action: Optional[str] = None,
        step_id: Optional[str] = None,
        metadata: Optional[Mapping[str, Any]] = None,
        pass_step: bool = False,
        outcome_name: Optional[str] = None,
        outcome_check: Optional[Callable[[ResultT], bool]] = None,
    ) -> Callable[[StateT], ResultT]:
        """Wrap a LangGraph node without importing LangGraph itself."""

        def wrapped(state: StateT) -> ResultT:
            def handler(step: AgentStep) -> ResultT:
                if pass_step:
                    return node(state, step)
                return node(state)

            return run_gated_step(
                self.run,
                agent or name,
                action or name,
                handler,
                step_id=step_id or name,
                metadata=metadata,
                outcome_name=outcome_name,
                outcome_check=outcome_check,
            )

        return wrapped

    def receipts(self) -> list[ConsistencyReceipt]:
        return self.run.receipts()
