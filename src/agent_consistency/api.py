from contextlib import nullcontext
from dataclasses import dataclass
from functools import wraps
from types import TracebackType
from typing import Any, Callable, Dict, Iterable, Literal, Mapping, Optional, Type, TypeVar, Union

from .models import ConsistencyReceipt
from .outcome import OutcomeVerifierProtocol
from .run import AgentStep, WorkflowRun

T = TypeVar("T")
OutcomeFactory = Union[OutcomeVerifierProtocol, Callable[[T], OutcomeVerifierProtocol]]


@dataclass(frozen=True)
class GateDecision:
    allowed: bool
    receipt: Optional[ConsistencyReceipt]
    reason: str = ""


class ReliabilityGate:
    def __init__(
        self,
        run: WorkflowRun,
        agent: str,
        action: str,
        *,
        step_id: Optional[str] = None,
        criticality: str = "high",
        idempotency_key: Optional[str] = None,
        state_name: Optional[str] = None,
        state_value: Any = None,
        state_version: Optional[Any] = None,
        current_version: Optional[Any] = None,
        handoff_facts: Optional[Mapping[str, Any]] = None,
        required_handoff_facts: Optional[Iterable[str]] = None,
        outcome_verifier: Optional[OutcomeVerifierProtocol] = None,
        metadata: Optional[Mapping[str, Any]] = None,
        tracer: Any = None,
    ) -> None:
        self.run = run
        self.agent = agent
        self.action = action
        self.step_id = step_id
        self.criticality = criticality
        self.idempotency_key = idempotency_key
        self.state_name = state_name
        self.state_value = state_value
        self.state_version = state_version
        self.current_version = current_version
        self.handoff_facts = dict(handoff_facts or {})
        self.required_handoff_facts = list(required_handoff_facts or [])
        self.outcome_verifier = outcome_verifier
        self.metadata = dict(metadata or {})
        self.tracer = tracer
        self.step: Optional[AgentStep] = None
        self.decision = GateDecision(allowed=False, receipt=None, reason="not started")
        self._step_cm: Optional[AgentStep] = None
        self._span_cm: Any = nullcontext(None)
        self._span: Any = None

    def __enter__(self) -> "ReliabilityGate":
        self._span_cm = self._start_span()
        self._span = self._span_cm.__enter__()
        self._step_cm = self.run.step(
            self.agent,
            self.action,
            step_id=self.step_id,
            criticality=self.criticality,
            idempotency_key=self.idempotency_key,
            metadata=self.metadata,
        )
        try:
            self.step = self._step_cm.__enter__()
            self._record_preconditions()
        except BaseException as exc:
            self._finish_step(type(exc), exc, exc.__traceback__)
            self._finish_span(type(exc), exc, exc.__traceback__)
            raise
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[TracebackType],
    ) -> Literal[False]:
        final_type = exc_type
        final_exc = exc
        final_tb = tb

        if final_exc is None and self.outcome_verifier is not None and self.step is not None:
            try:
                self.step.verify_outcome_with(
                    self.outcome_verifier,
                    criticality=self.criticality,
                )
            except BaseException as verifier_exc:
                final_type = type(verifier_exc)
                final_exc = verifier_exc
                final_tb = verifier_exc.__traceback__

        self._finish_step(final_type, final_exc, final_tb)
        self._finish_span(final_type, final_exc, final_tb)

        if exc is None and final_exc is not None:
            raise final_exc
        return False

    def verify_result(self, result: T, outcome_factory: OutcomeFactory[T]) -> None:
        if self.step is None:
            raise RuntimeError("reliability gate is not active")
        verifier = outcome_factory(result) if callable(outcome_factory) else outcome_factory
        self.step.verify_outcome_with(verifier, criticality=self.criticality)

    def _record_preconditions(self) -> None:
        if self.step is None:
            return
        if self.state_name is not None:
            snapshot = self.step.read_state(
                self.state_name,
                self.state_value,
                version=self.state_version,
            )
            if self.current_version is not None:
                self.step.ensure_fresh(snapshot, current_version=self.current_version)
        if self.required_handoff_facts:
            self.step.handoff(
                to_agent=self.agent,
                task=self.action,
                facts=self.handoff_facts,
                required_facts=self.required_handoff_facts,
            )

    def _finish_step(
        self,
        exc_type: Optional[Type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[TracebackType],
    ) -> None:
        if self._step_cm is None:
            return
        self._step_cm.__exit__(exc_type, exc, tb)
        receipt = self.step.receipt if self.step is not None else None
        allowed = exc is None
        reason = "allowed" if allowed else str(exc)
        self.decision = GateDecision(allowed=allowed, receipt=receipt, reason=reason)

    def _start_span(self) -> Any:
        tracer = self.tracer or _optional_tracer()
        if tracer is None:
            return nullcontext(None)
        return tracer.start_as_current_span(
            "agent_consistency.gate",
            attributes={
                "gen_ai.operation.name": self.action,
                "gen_ai.system": "agent-consistency",
                "agent_consistency.run_id": self.run.run_id,
                "agent_consistency.agent": self.agent,
                "agent_consistency.action": self.action,
                "agent_consistency.criticality": self.criticality,
            },
        )

    def _finish_span(
        self,
        exc_type: Optional[Type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[TracebackType],
    ) -> None:
        if self._span is not None and self.step is not None:
            receipt = self.step.receipt
            latest_policy: Dict[str, Any] = (
                receipt.policy_decisions[-1] if receipt.policy_decisions else {}
            )
            _set_span_attribute(self._span, "agent_consistency.step_id", receipt.step_id)
            _set_span_attribute(self._span, "agent_consistency.status", receipt.status)
            _set_span_attribute(
                self._span,
                "agent_consistency.policy.mode",
                latest_policy.get("mode", ""),
            )
        self._span_cm.__exit__(exc_type, exc, tb)


def reliability_gate(
    run: WorkflowRun,
    agent: str,
    action: str,
    **kwargs: Any,
) -> ReliabilityGate:
    return ReliabilityGate(run, agent, action, **kwargs)


def verified_step(
    run: WorkflowRun,
    agent: str,
    action: str,
    *,
    outcome_verifier: Optional[OutcomeFactory[T]] = None,
    **gate_kwargs: Any,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            with reliability_gate(run, agent, action, **gate_kwargs) as gate:
                result = func(*args, **kwargs)
                if outcome_verifier is not None:
                    gate.verify_result(result, outcome_verifier)
                return result

        return wrapper

    return decorator


def _optional_tracer() -> Any:
    try:
        from opentelemetry import trace
    except ImportError:
        return None
    return trace.get_tracer("agent_consistency.api")


def _set_span_attribute(span: Any, key: str, value: Any) -> None:
    setter = getattr(span, "set_attribute", None)
    if callable(setter):
        setter(key, value)
