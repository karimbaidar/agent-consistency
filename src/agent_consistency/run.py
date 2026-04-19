import uuid
import warnings
from collections.abc import Iterable, Mapping
from typing import Any, Callable, Dict, Literal, Optional

from .errors import HandoffValidationError, OutcomeVerificationError, StaleStateError
from .handoff import HandoffPacket
from .models import ConsistencyIssue, ConsistencyReceipt, OutcomeResult, StateDelta, StateSnapshot
from .outcome import OutcomeCheck, OutcomeVerifier
from .store import InMemoryReceiptStore, ReceiptStore

_MISSING = object()


class WorkflowRun:
    def __init__(
        self,
        run_id: Optional[str] = None,
        *,
        store: Optional[ReceiptStore] = None,
        on_violation: str = "raise",
    ) -> None:
        if on_violation not in {"raise", "warn", "record"}:
            raise ValueError("on_violation must be one of: raise, warn, record")
        self.run_id = run_id or str(uuid.uuid4())
        self.store = store or InMemoryReceiptStore()
        self.on_violation = on_violation

    def step(
        self,
        agent: str,
        action: str,
        *,
        step_id: Optional[str] = None,
        assumptions: Optional[Iterable[str]] = None,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> "AgentStep":
        return AgentStep(
            self,
            agent=agent,
            action=action,
            step_id=step_id,
            assumptions=assumptions,
            metadata=metadata,
        )

    def receipts(self) -> list:
        return self.store.list(run_id=self.run_id)

    def _record(self, receipt: ConsistencyReceipt) -> None:
        self.store.add(receipt)


class AgentStep:
    def __init__(
        self,
        run: WorkflowRun,
        *,
        agent: str,
        action: str,
        step_id: Optional[str] = None,
        assumptions: Optional[Iterable[str]] = None,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> None:
        self.run = run
        self.receipt = ConsistencyReceipt(
            run_id=run.run_id,
            step_id=step_id or f"{agent}:{action}:{uuid.uuid4().hex[:8]}",
            agent=agent,
            action=action,
            assumptions=list(assumptions or []),
            metadata=dict(metadata or {}),
        )

    def __enter__(self) -> "AgentStep":
        return self

    def __exit__(self, exc_type: Any, exc: Optional[BaseException], tb: Any) -> Literal[False]:
        self.receipt.finish(error=exc)
        self.run._record(self.receipt)
        return False

    def read_state(
        self,
        name: str,
        value: Any,
        *,
        version: Optional[Any] = None,
        include_value: bool = False,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> StateSnapshot:
        snapshot = StateSnapshot.capture(
            name,
            value,
            version=version,
            include_value=include_value,
            metadata=metadata,
        )
        self.receipt.state_reads.append(snapshot)
        return snapshot

    def ensure_fresh(
        self,
        snapshot: StateSnapshot,
        *,
        current: Optional[StateSnapshot] = None,
        current_value: Any = _MISSING,
        current_version: Optional[Any] = None,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> bool:
        if current is None and current_value is not _MISSING:
            current = StateSnapshot.capture(snapshot.name, current_value, version=current_version)
        if current is not None:
            is_fresh = snapshot.same_version_as(current)
            current_details: Any = current.to_dict()
        elif current_version is not None:
            is_fresh = snapshot.version == str(current_version)
            current_details = {"name": snapshot.name, "version": str(current_version)}
        else:
            raise ValueError("provide current, current_value, or current_version")

        if is_fresh:
            return True

        details = {
            "snapshot": snapshot.to_dict(),
            "current": current_details,
        }
        if metadata:
            details["metadata"] = dict(metadata)
        message = (
            f"state '{snapshot.name}' is stale: read version {snapshot.version}, "
            f"current version {current_details.get('version')}"
        )

        def factory(text: str) -> StaleStateError:
            return StaleStateError(text, snapshot=snapshot, current=current)

        self._handle_issue(
            code="stale_state",
            message=message,
            details=details,
            exception_factory=factory,
        )
        return False

    def write_state(
        self,
        name: str,
        value: Any,
        *,
        based_on: Optional[StateSnapshot] = None,
        current: Optional[StateSnapshot] = None,
        current_value: Any = _MISSING,
        current_version: Optional[Any] = None,
        version: Optional[Any] = None,
        operation: str = "write",
        include_value: bool = False,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> StateDelta:
        if based_on is not None and (
            current is not None or current_value is not _MISSING or current_version is not None
        ):
            self.ensure_fresh(
                based_on,
                current=current,
                current_value=current_value,
                current_version=current_version,
            )
        after = StateSnapshot.capture(
            name,
            value,
            version=version,
            include_value=include_value,
            metadata=metadata,
        )
        delta = StateDelta(
            name=name,
            before=based_on,
            after=after,
            operation=operation,
            metadata=dict(metadata or {}),
        )
        self.receipt.state_deltas.append(delta)
        return delta

    def handoff(
        self,
        *,
        to_agent: str,
        task: str,
        facts: Optional[Mapping[str, Any]] = None,
        assumptions: Optional[Iterable[str]] = None,
        missing_info: Optional[Iterable[str]] = None,
        constraints: Optional[Iterable[str]] = None,
        evidence: Optional[Mapping[str, Any]] = None,
        metadata: Optional[Mapping[str, Any]] = None,
        required_facts: Optional[Iterable[str]] = None,
        required_assumptions: Optional[Iterable[str]] = None,
        required_constraints: Optional[Iterable[str]] = None,
        required_evidence: Optional[Iterable[str]] = None,
    ) -> HandoffPacket:
        packet = HandoffPacket(
            from_agent=self.receipt.agent,
            to_agent=to_agent,
            task=task,
            facts=dict(facts or {}),
            assumptions=list(assumptions or []),
            missing_info=list(missing_info or []),
            constraints=list(constraints or []),
            evidence=dict(evidence or {}),
            metadata=dict(metadata or {}),
        )
        self.receipt.handoffs.append(packet)
        problems = packet.validate(
            required_facts=required_facts,
            required_assumptions=required_assumptions,
            required_constraints=required_constraints,
            required_evidence=required_evidence,
        )
        if problems:
            message = "; ".join(problems)
            self._handle_issue(
                code="invalid_handoff",
                message=message,
                details={"handoff": packet.to_dict(), "problems": problems},
                exception_factory=lambda text: HandoffValidationError(
                    text,
                    details={"problems": problems},
                ),
            )
        return packet

    def require_supported_claims(
        self,
        packet: HandoffPacket,
        claims: Mapping[str, Any],
        *,
        by: Iterable[str],
    ) -> bool:
        problems = packet.require_supported_claims(claims, by=by)
        if not problems:
            return True
        self._handle_issue(
            code="unsupported_claim",
            message="; ".join(problems),
            details={
                "claims": dict(claims),
                "support_keys": list(by),
                "handoff": packet.to_dict(),
            },
            exception_factory=lambda text: HandoffValidationError(
                text,
                details={"problems": problems},
            ),
        )
        return False

    def verify_outcome(
        self,
        name: str,
        check: OutcomeCheck,
        *,
        success_reason: str = "postcondition passed",
        failure_reason: str = "postcondition failed",
        details: Optional[Dict[str, Any]] = None,
    ) -> OutcomeResult:
        result = OutcomeVerifier(
            name,
            check,
            success_reason=success_reason,
            failure_reason=failure_reason,
            details=details,
        ).run()
        self.receipt.outcomes.append(result)
        if not result.passed:
            self._handle_issue(
                code="outcome_failed",
                message=f"outcome '{name}' failed: {result.reason}",
                details=result.to_dict(),
                exception_factory=lambda text: OutcomeVerificationError(text, result=result),
            )
        return result

    def _handle_issue(
        self,
        *,
        code: str,
        message: str,
        details: Mapping[str, Any],
        exception_factory: Callable[[str], BaseException],
    ) -> None:
        issue = ConsistencyIssue(
            code=code,
            message=message,
            severity="warning" if self.run.on_violation == "warn" else "error",
            details=dict(details),
        )
        self.receipt.issues.append(issue)
        if self.run.on_violation == "warn":
            warnings.warn(message, RuntimeWarning, stacklevel=3)
            return
        if self.run.on_violation == "record":
            return
        raise exception_factory(message)
