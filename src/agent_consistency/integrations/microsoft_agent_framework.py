import inspect
from collections.abc import AsyncIterable, Awaitable, Callable, Mapping
from typing import Any, Optional, TypeVar, Union

from ..api import reliability_gate
from ..handoff import HandoffPacket
from ..models import ConsistencyReceipt
from ..outcome import OutcomeVerifierProtocol
from ..run import WorkflowRun
from ..store import ReceiptStore

ResultT = TypeVar("ResultT")
IdempotencyKey = Union[str, Callable[[Any], Optional[str]]]


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

    def receipts(self, *, run_id: Optional[str] = None) -> list[ConsistencyReceipt]:
        return self.run.store.list(run_id=run_id)


class MicrosoftAgentFrameworkNativeIntegration(MicrosoftAgentFrameworkConsistencyAdapter):
    """Native MAF-shaped integration for async agents, middleware, and streams.

    The real `agent-framework` package is optional and imported by user code. This
    class targets the documented Python seams: `Agent.run(...)`, async middleware
    accepting `(context, call_next)`, and async streaming methods.
    """

    def wrap_agent_run(
        self,
        agent_obj: Any,
        *,
        method: str = "run",
        agent: Optional[str] = None,
        action: Optional[str] = None,
        step_id: Optional[str] = None,
        criticality: str = "high",
        idempotency_key: Optional[IdempotencyKey] = None,
        metadata: Optional[Mapping[str, Any]] = None,
        outcome_name: Optional[str] = None,
        outcome_check: Optional[Callable[[Any], bool]] = None,
        outcome_verifier: Optional[Callable[[Any], OutcomeVerifierProtocol]] = None,
        result_extractor: Optional[Callable[[Any], Any]] = None,
    ) -> Callable[..., Awaitable[Any]]:
        """Wrap a real MAF `Agent.run(...)`-style async method."""
        handler = getattr(agent_obj, method)
        agent_name = agent or getattr(agent_obj, "name", agent_obj.__class__.__name__)

        async def wrapped(*args: Any, **kwargs: Any) -> Any:
            context = _first_context(args, kwargs)
            run = self._run_for_context(context)
            with reliability_gate(
                run,
                agent_name,
                action or method,
                step_id=step_id or _context_value(context, "step_id", "invocation_id"),
                criticality=criticality,
                idempotency_key=_resolve_idempotency_key(idempotency_key, context),
                metadata=_merge_metadata(metadata, _context_metadata(context)),
            ) as gate:
                result = await _maybe_await(handler(*args, **kwargs))
                verification_target = result_extractor(result) if result_extractor else result
                _verify_result(
                    gate,
                    verification_target,
                    criticality=criticality,
                    outcome_name=outcome_name,
                    outcome_check=outcome_check,
                    outcome_verifier=outcome_verifier,
                )
                return result

        return wrapped

    def wrap_agent_stream(
        self,
        agent_obj: Any,
        *,
        method: str = "run_stream",
        agent: Optional[str] = None,
        action: Optional[str] = None,
        step_id: Optional[str] = None,
        criticality: str = "high",
        idempotency_key: Optional[IdempotencyKey] = None,
        metadata: Optional[Mapping[str, Any]] = None,
        outcome_name: Optional[str] = None,
        outcome_check: Optional[Callable[[Any], bool]] = None,
        outcome_verifier: Optional[Callable[[Any], OutcomeVerifierProtocol]] = None,
        stream_result_reducer: Optional[Callable[[list[Any]], Any]] = None,
    ) -> Callable[..., AsyncIterable[Any]]:
        """Wrap a MAF streaming method while preserving chunk delivery."""
        handler = getattr(agent_obj, method)
        agent_name = agent or getattr(agent_obj, "name", agent_obj.__class__.__name__)

        async def wrapped(*args: Any, **kwargs: Any) -> AsyncIterable[Any]:
            context = _first_context(args, kwargs)
            run = self._run_for_context(context)
            chunks: list[Any] = []
            with reliability_gate(
                run,
                agent_name,
                action or method,
                step_id=step_id or _context_value(context, "step_id", "invocation_id"),
                criticality=criticality,
                idempotency_key=_resolve_idempotency_key(idempotency_key, context),
                metadata=_merge_metadata(metadata, _context_metadata(context)),
            ) as gate:
                stream = await _maybe_await(handler(*args, **kwargs))
                async for chunk in _iter_stream(stream):
                    chunks.append(chunk)
                    yield chunk
                verification_target = (
                    stream_result_reducer(chunks)
                    if stream_result_reducer is not None
                    else (chunks[-1] if chunks else None)
                )
                _verify_result(
                    gate,
                    verification_target,
                    criticality=criticality,
                    outcome_name=outcome_name,
                    outcome_check=outcome_check,
                    outcome_verifier=outcome_verifier,
                )

        return wrapped

    def agent_middleware(
        self,
        *,
        agent: Optional[str] = None,
        action: str = "agent.run",
        step_id: Optional[str] = None,
        criticality: str = "high",
        idempotency_key: Optional[IdempotencyKey] = None,
        metadata: Optional[Mapping[str, Any]] = None,
        outcome_name: Optional[str] = None,
        outcome_check: Optional[Callable[[Any], bool]] = None,
        outcome_verifier: Optional[Callable[[Any], OutcomeVerifierProtocol]] = None,
        result_extractor: Optional[Callable[[Any], Any]] = None,
    ) -> Callable[[Any, Callable[[], Awaitable[None]]], Awaitable[None]]:
        """Return async MAF agent middleware `(context, call_next) -> None`."""

        async def middleware(context: Any, call_next: Callable[[], Awaitable[None]]) -> None:
            run = self._run_for_context(context)
            agent_name = agent or _context_value(context, "agent_name", "name") or "maf-agent"
            with reliability_gate(
                run,
                str(agent_name),
                action,
                step_id=step_id or _context_value(context, "step_id", "invocation_id"),
                criticality=criticality,
                idempotency_key=_resolve_idempotency_key(idempotency_key, context),
                metadata=_merge_metadata(metadata, _context_metadata(context)),
            ) as gate:
                await _maybe_await(call_next())
                result = result_extractor(context) if result_extractor else _context_result(context)
                _verify_result(
                    gate,
                    result,
                    criticality=criticality,
                    outcome_name=outcome_name,
                    outcome_check=outcome_check,
                    outcome_verifier=outcome_verifier,
                )

        return middleware

    def function_middleware(
        self,
        *,
        agent: str = "maf-tool",
        action: Optional[str] = None,
        step_id: Optional[str] = None,
        criticality: str = "high",
        idempotency_key: Optional[IdempotencyKey] = None,
        metadata: Optional[Mapping[str, Any]] = None,
        outcome_name: Optional[str] = None,
        outcome_check: Optional[Callable[[Any], bool]] = None,
        outcome_verifier: Optional[Callable[[Any], OutcomeVerifierProtocol]] = None,
        result_extractor: Optional[Callable[[Any], Any]] = None,
    ) -> Callable[[Any, Callable[[], Awaitable[None]]], Awaitable[None]]:
        """Return async MAF function/tool middleware `(context, call_next) -> None`."""

        async def middleware(context: Any, call_next: Callable[[], Awaitable[None]]) -> None:
            run = self._run_for_context(context)
            function_name = _function_name(context) or action or "maf-function"
            with reliability_gate(
                run,
                agent,
                action or function_name,
                step_id=step_id or _context_value(context, "step_id", "invocation_id"),
                criticality=criticality,
                idempotency_key=_resolve_idempotency_key(idempotency_key, context),
                metadata=_merge_metadata(metadata, _context_metadata(context)),
            ) as gate:
                await _maybe_await(call_next())
                result = result_extractor(context) if result_extractor else _context_result(context)
                _verify_result(
                    gate,
                    result,
                    criticality=criticality,
                    outcome_name=outcome_name,
                    outcome_check=outcome_check,
                    outcome_verifier=outcome_verifier,
                )

        return middleware

    def _run_for_context(self, context: Any) -> WorkflowRun:
        run_id = _context_value(context, "run_id", "session_id", "thread_id") or self.run.run_id
        if str(run_id) == self.run.run_id:
            return self.run
        return WorkflowRun(
            str(run_id),
            store=self.run.store,
            on_violation=self.run.on_violation,
            failure_policy=self.run.failure_policy,
        )


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


async def _iter_stream(stream: Any) -> AsyncIterable[Any]:
    if hasattr(stream, "__aiter__"):
        async for item in stream:
            yield item
        return
    for item in stream:
        yield item


def _verify_result(
    gate: Any,
    result: Any,
    *,
    criticality: str,
    outcome_name: Optional[str],
    outcome_check: Optional[Callable[[Any], bool]],
    outcome_verifier: Optional[Callable[[Any], OutcomeVerifierProtocol]],
) -> None:
    if outcome_verifier is not None:
        gate.verify_result(result, outcome_verifier)
    elif outcome_name and outcome_check and gate.step is not None:
        gate.step.verify_outcome(
            outcome_name,
            lambda: outcome_check(result),
            criticality=criticality,
        )


def _first_context(args: tuple[Any, ...], kwargs: Mapping[str, Any]) -> Any:
    if args:
        return args[0]
    for name in ("context", "ctx", "request"):
        if name in kwargs:
            return kwargs[name]
    return None


def _resolve_idempotency_key(key: Optional[IdempotencyKey], context: Any) -> Optional[str]:
    if key is None:
        value = _context_value(context, "idempotency_key")
        return str(value) if value is not None else None
    if callable(key):
        value = key(context)
        return str(value) if value is not None else None
    return str(key)


def _context_metadata(context: Any) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    for name in (
        "run_id",
        "session_id",
        "thread_id",
        "invocation_id",
        "request_id",
        "user_id",
    ):
        value = _context_value(context, name)
        if value is not None:
            metadata[name] = value
    for name in ("metadata", "data", "variables"):
        value = _context_value(context, name)
        if isinstance(value, Mapping):
            metadata[name] = dict(value)
    return metadata


def _merge_metadata(
    explicit: Optional[Mapping[str, Any]],
    inferred: Mapping[str, Any],
) -> dict[str, Any]:
    merged = dict(inferred)
    merged.update(dict(explicit or {}))
    return merged


def _context_result(context: Any) -> Any:
    for name in ("result", "response", "output", "value"):
        value = _context_value(context, name)
        if value is not None:
            return value
    return None


def _function_name(context: Any) -> Optional[str]:
    function = _context_value(context, "function")
    value = _context_value(function, "name") if function is not None else None
    return str(value) if value is not None else None


def _context_value(context: Any, *names: str) -> Any:
    if context is None:
        return None
    for name in names:
        value = _get_value(context, name)
        if value is not None:
            return value
    for container_name in ("session", "run", "request", "context"):
        container = _get_value(context, container_name)
        if container is not None and container is not context:
            value = _context_value(container, *names)
            if value is not None:
                return value
    return None


def _get_value(source: Any, name: str) -> Any:
    if source is None:
        return None
    if isinstance(source, Mapping):
        return source.get(name)
    return getattr(source, name, None)
