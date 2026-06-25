from collections.abc import Callable, Mapping
from typing import Any, Optional, TypeVar

from ..api import reliability_gate
from ..handoff import HandoffPacket
from ..models import ConsistencyReceipt
from ..outcome import OutcomeVerifierProtocol
from ..run import WorkflowRun
from ..store import ReceiptStore

ResultT = TypeVar("ResultT")


class MicrosoftAgentFrameworkConsistencyAdapter:
    """Dependency-light adapter for Microsoft Agent Framework-shaped callables."""

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
    ) -> "MicrosoftAgentFrameworkConsistencyAdapter":
        return cls(WorkflowRun.detect(run_id, store=store))

    def wrap_agent_method(
        self,
        agent_obj: Any,
        *,
        method: str = "invoke",
        agent: Optional[str] = None,
        action: Optional[str] = None,
        step_id: Optional[str] = None,
        criticality: str = "high",
        idempotency_key: Optional[str] = None,
        metadata: Optional[Mapping[str, Any]] = None,
        pass_step: bool = False,
        outcome_name: Optional[str] = None,
        outcome_check: Optional[Callable[[ResultT], bool]] = None,
        outcome_verifier: Optional[Callable[[ResultT], OutcomeVerifierProtocol]] = None,
    ) -> Callable[..., ResultT]:
        """Wrap an agent object's method, such as invoke/run/handle."""
        handler = getattr(agent_obj, method)
        agent_name = agent or getattr(agent_obj, "name", agent_obj.__class__.__name__)
        return self.wrap_callable(
            handler,
            agent=agent_name,
            action=action or method,
            step_id=step_id,
            criticality=criticality,
            idempotency_key=idempotency_key,
            metadata=metadata,
            pass_step=pass_step,
            outcome_name=outcome_name,
            outcome_check=outcome_check,
            outcome_verifier=outcome_verifier,
        )

    def wrap_callable(
        self,
        handler: Callable[..., ResultT],
        *,
        agent: str,
        action: str,
        step_id: Optional[str] = None,
        criticality: str = "high",
        idempotency_key: Optional[str] = None,
        metadata: Optional[Mapping[str, Any]] = None,
        pass_step: bool = False,
        outcome_name: Optional[str] = None,
        outcome_check: Optional[Callable[[ResultT], bool]] = None,
        outcome_verifier: Optional[Callable[[ResultT], OutcomeVerifierProtocol]] = None,
    ) -> Callable[..., ResultT]:
        """Wrap a MAF handler without importing Microsoft Agent Framework."""

        def wrapped(*args: Any, **kwargs: Any) -> ResultT:
            with reliability_gate(
                self.run,
                agent,
                action,
                step_id=step_id or action,
                criticality=criticality,
                idempotency_key=idempotency_key,
                metadata=metadata,
            ) as gate:
                if pass_step:
                    kwargs_with_step = dict(kwargs)
                    kwargs_with_step["step"] = gate.step
                    result = handler(*args, **kwargs_with_step)
                else:
                    result = handler(*args, **kwargs)
                if outcome_verifier is not None:
                    gate.verify_result(result, outcome_verifier)
                elif outcome_name and outcome_check and gate.step is not None:
                    gate.step.verify_outcome(
                        outcome_name,
                        lambda: outcome_check(result),
                        criticality=criticality,
                    )
                return result

        return wrapped

    def record_handoff(
        self,
        *,
        from_agent: str,
        to_agent: str,
        task: str,
        facts: Optional[Mapping[str, Any]] = None,
        required_facts: Optional[list[str]] = None,
        step_id: Optional[str] = None,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> HandoffPacket:
        """Record a MAF-style handoff contract before invoking the next agent."""
        with self.run.step(
            from_agent,
            f"handoff:{task}",
            step_id=step_id or f"handoff:{from_agent}:{to_agent}:{task}",
            metadata=metadata,
        ) as step:
            return step.handoff(
                to_agent=to_agent,
                task=task,
                facts=facts,
                required_facts=required_facts,
            )

    def receipts(self) -> list[ConsistencyReceipt]:
        return self.run.receipts()

