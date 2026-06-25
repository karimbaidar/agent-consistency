import uuid
import warnings
from collections.abc import Iterable, Mapping
from typing import Any, Callable, Dict, Literal, Optional

from .contracts import HandoffContract
from .errors import HandoffValidationError, OutcomeVerificationError, StaleStateError
from .handoff import HandoffPacket
from .models import (
    ConsistencyIssue,
    ConsistencyReceipt,
    OutcomeResult,
    ProofArtifact,
    StateDelta,
    StateSnapshot,
)
from .outcome import OutcomeCheck, OutcomeVerifier, OutcomeVerifierProtocol
from .policy import DEFAULT_FAILURE_POLICY, FailurePolicy
from .store import InMemoryReceiptStore, ReceiptStore
from .verifier import VerificationContext, VerifierRegistry

_MISSING = object()


class WorkflowRun:
    def __init__(
        self,
        run_id: Optional[str] = None,
        *,
        store: Optional[ReceiptStore] = None,
        on_violation: str = "raise",
        failure_policy: Optional[FailurePolicy] = None,
    ) -> None:
        if on_violation not in {"raise", "warn", "record", "report", "detect"}:
            raise ValueError(
                "on_violation must be one of: raise, warn, record, report, detect"
            )
        self.run_id = run_id or str(uuid.uuid4())
        self.store = store or InMemoryReceiptStore()
        self.on_violation = on_violation
        self.failure_policy = failure_policy or DEFAULT_FAILURE_POLICY
        self._idempotency_keys: set[str] = set()

    @classmethod
    def detect(
        cls,
        run_id: Optional[str] = None,
        *,
        store: Optional[ReceiptStore] = None,
    ) -> "WorkflowRun":
        """Create a non-blocking run for false-success risk reporting."""
        return cls(run_id, store=store, on_violation="report")

    def step(
        self,
        agent: str,
        action: str,
        *,
        step_id: Optional[str] = None,
        assumptions: Optional[Iterable[str]] = None,
        criticality: str = "high",
        idempotency_key: Optional[str] = None,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> "AgentStep":
        return AgentStep(
            self,
            agent=agent,
            action=action,
            step_id=step_id,
            assumptions=assumptions,
            criticality=criticality,
            idempotency_key=idempotency_key,
            metadata=metadata,
        )

    def receipts(self) -> list:
        return self.store.list(run_id=self.run_id)

    def _record(self, receipt: ConsistencyReceipt) -> None:
        self.store.add(receipt)

    def flush(self) -> None:
        flush = getattr(self.store, "flush", None)
        if callable(flush):
            flush()


class AgentStep:
    def __init__(
        self,
        run: WorkflowRun,
        *,
        agent: str,
        action: str,
        step_id: Optional[str] = None,
        assumptions: Optional[Iterable[str]] = None,
        criticality: str = "high",
        idempotency_key: Optional[str] = None,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> None:
        self.run = run
        self.criticality = criticality
        self._duplicate_idempotency_key = (
            idempotency_key is not None and idempotency_key in run._idempotency_keys
        )
        if idempotency_key is not None and not self._duplicate_idempotency_key:
            run._idempotency_keys.add(idempotency_key)
        self.receipt = ConsistencyReceipt(
            run_id=run.run_id,
            step_id=step_id or f"{agent}:{action}:{uuid.uuid4().hex[:8]}",
            agent=agent,
            action=action,
            assumptions=list(assumptions or []),
            idempotency_key=idempotency_key,
            metadata=dict(metadata or {}),
        )
        self.receipt.metadata.setdefault("criticality", criticality)

    def __enter__(self) -> "AgentStep":
        if self._duplicate_idempotency_key:
            try:
                self._handle_issue(
                    code="duplicate_idempotency_key",
                    message=f"idempotency key already used: {self.receipt.idempotency_key}",
                    details={"idempotency_key": self.receipt.idempotency_key},
                    exception_factory=lambda text: OutcomeVerificationError(text),
                    criticality="financial",
                )
                raise OutcomeVerificationError(
                    f"idempotency key already used: {self.receipt.idempotency_key}"
                )
            finally:
                self.receipt.finish()
                self.run._record(self.receipt)
        return self

    def __exit__(self, exc_type: Any, exc: Optional[BaseException], tb: Any) -> Literal[False]:
        self.receipt.finish(error=exc)
        self.run._record(self.receipt)
        if exc is not None or self.receipt.status == "failed":
            self.run.flush()
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

    def proof_artifact(
        self,
        name: str,
        value: Any,
        *,
        kind: str = "data",
        verified: bool = False,
        uri: Optional[str] = None,
        verifier: Optional[str] = None,
        details: Optional[Mapping[str, Any]] = None,
        include_value: bool = False,
    ) -> ProofArtifact:
        artifact = ProofArtifact.capture(
            name,
            value,
            kind=kind,
            verified=verified,
            uri=uri,
            verifier=verifier,
            details=details,
            include_value=include_value,
        )
        self.receipt.proof_artifacts.append(artifact)
        return artifact

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
        artifacts: Optional[Iterable[ProofArtifact]] = None,
        contract: Optional[HandoffContract] = None,
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
            artifacts=list(artifacts or []),
            contract=contract,
            produced_by_receipt=self.receipt.key,
            metadata=dict(metadata or {}),
        )
        self.receipt.handoffs.append(packet)
        self.receipt.produced_handoff_ids.append(packet.handoff_id)
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

    def consume_handoff(
        self,
        packet: HandoffPacket,
        *,
        contract: Optional[HandoffContract] = None,
        require_verified: bool = True,
        registry: Optional[VerifierRegistry] = None,
        verifier: Optional[str] = None,
    ) -> bool:
        active_contract = contract or packet.contract
        problems = packet.validate(
            required_facts=active_contract.required_facts if active_contract else None,
            required_assumptions=active_contract.required_assumptions if active_contract else None,
            required_constraints=active_contract.required_constraints if active_contract else None,
            required_evidence=active_contract.required_evidence if active_contract else None,
        )
        if active_contract:
            problems.extend(active_contract.validate_artifacts(packet.artifacts))
        if require_verified and not packet.verified:
            problems.append(f"handoff '{packet.handoff_id}' is not verified")
        if active_contract and packet.contract and active_contract.name != packet.contract.name:
            problems.append(
                f"handoff contract mismatch: expected '{active_contract.name}', "
                f"got '{packet.contract.name}'"
            )

        if problems:
            self._handle_issue(
                code="invalid_consumed_handoff",
                message="; ".join(problems),
                details={"handoff": packet.to_dict(), "problems": problems},
                exception_factory=lambda text: HandoffValidationError(
                    text,
                    details={"problems": problems},
                ),
            )
            return False

        self.receipt.consumed_handoff_ids.append(packet.handoff_id)
        self.receipt.consumed_artifact_ids.extend(
            artifact.artifact_id for artifact in packet.artifacts
        )
        if packet.produced_by_receipt:
            self.receipt.parent_receipt_keys.append(packet.produced_by_receipt)

        verifier_name = verifier or (active_contract.verifier if active_contract else None)
        if registry and verifier_name:
            result = registry.verify(
                verifier_name,
                VerificationContext(
                    name=verifier_name,
                    receipt=self.receipt,
                    subject=packet,
                    facts=packet.facts,
                    metadata={"contract": active_contract.to_dict() if active_contract else None},
                ),
            )
            self.receipt.outcomes.append(result)
            if not result.passed:
                self._handle_issue(
                    code="handoff_verifier_failed",
                    message=f"handoff verifier '{verifier_name}' failed: {result.reason}",
                    details=result.to_dict(),
                    exception_factory=lambda text: HandoffValidationError(
                        text,
                        details=result.details,
                    ),
                )
                return False
        return True

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
        criticality: Optional[str] = None,
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
                criticality=criticality,
            )
        return result

    def verify_outcome_with(
        self,
        verifier: OutcomeVerifierProtocol,
        *,
        criticality: Optional[str] = None,
    ) -> OutcomeResult:
        verifier_error: Optional[BaseException] = None
        try:
            result = verifier.run()
        except Exception as exc:
            verifier_error = exc
            result = OutcomeResult(
                name=verifier.name,
                passed=False,
                reason=f"outcome verifier error: {exc.__class__.__name__}: {exc}",
                details={"error_type": exc.__class__.__name__, "error": str(exc)},
            )
        self.receipt.outcomes.append(result)
        if not result.passed:
            self._handle_issue(
                code="outcome_failed",
                message=f"outcome '{result.name}' failed: {result.reason}",
                details=result.to_dict(),
                exception_factory=lambda text: OutcomeVerificationError(text, result=result),
                criticality=criticality,
                error=verifier_error,
            )
        return result

    def verify_with(
        self,
        registry: VerifierRegistry,
        name: str,
        *,
        subject: Any = None,
        facts: Optional[Mapping[str, Any]] = None,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> OutcomeResult:
        result = registry.verify(
            name,
            VerificationContext(
                name=name,
                receipt=self.receipt,
                subject=subject,
                facts=facts,
                metadata=metadata,
            ),
        )
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
        criticality: Optional[str] = None,
        error: Optional[BaseException] = None,
    ) -> None:
        decision = self.run.failure_policy.resolve(
            criticality or self.criticality,
            reason=message,
            error=error,
        )
        self.receipt.policy_decisions.append(decision.to_dict())
        issue = ConsistencyIssue(
            code=code,
            message=message,
            severity=(
                "warning"
                if self.run.on_violation == "warn" or decision.mode == "fail_open"
                else "error"
            ),
            details={**dict(details), "policy": decision.to_dict()},
        )
        self.receipt.issues.append(issue)
        if decision.mode == "fail_closed":
            self.run.flush()
        if self.run.on_violation == "warn" or decision.mode == "fail_open":
            warnings.warn(message, RuntimeWarning, stacklevel=3)
            return
        if self.run.on_violation in {"record", "report", "detect"}:
            return
        raise exception_factory(message)
