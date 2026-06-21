from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ._time import utc_now_iso
from .serialization import stable_digest, to_jsonable

RECEIPT_SCHEMA_VERSION = "1"
RECEIPT_DIGEST_FIELD = "receipt_digest"


def canonical_receipt_payload(payload: Mapping[str, Any]) -> Dict[str, Any]:
    canonical = dict(payload)
    canonical.pop(RECEIPT_DIGEST_FIELD, None)
    return canonical


def compute_receipt_digest(payload: Mapping[str, Any]) -> str:
    return stable_digest(canonical_receipt_payload(payload))


@dataclass(frozen=True)
class StateSnapshot:
    name: str
    version: str
    digest: str
    captured_at: str = field(default_factory=utc_now_iso)
    metadata: Dict[str, Any] = field(default_factory=dict)
    value: Optional[Any] = field(default=None, repr=False, compare=False)

    @classmethod
    def capture(
        cls,
        name: str,
        value: Any,
        *,
        version: Optional[Any] = None,
        include_value: bool = False,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> "StateSnapshot":
        digest = stable_digest(value)
        return cls(
            name=name,
            version=str(version) if version is not None else digest[:12],
            digest=digest,
            metadata=dict(metadata or {}),
            value=to_jsonable(value) if include_value else None,
        )

    def same_version_as(self, other: "StateSnapshot") -> bool:
        return (
            self.name == other.name
            and self.version == other.version
            and self.digest == other.digest
        )

    def to_dict(self) -> Dict[str, Any]:
        payload = {
            "name": self.name,
            "version": self.version,
            "digest": self.digest,
            "captured_at": self.captured_at,
            "metadata": to_jsonable(self.metadata),
        }
        if self.value is not None:
            payload["value"] = self.value
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "StateSnapshot":
        return cls(
            name=str(payload["name"]),
            version=str(payload["version"]),
            digest=str(payload["digest"]),
            captured_at=str(payload.get("captured_at") or utc_now_iso()),
            metadata=dict(payload.get("metadata") or {}),
            value=payload.get("value"),
        )


@dataclass(frozen=True)
class StateDelta:
    name: str
    after: StateSnapshot
    before: Optional[StateSnapshot] = None
    operation: str = "write"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "operation": self.operation,
            "before": self.before.to_dict() if self.before else None,
            "after": self.after.to_dict(),
            "metadata": to_jsonable(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "StateDelta":
        before_payload = payload.get("before")
        return cls(
            name=str(payload["name"]),
            operation=str(payload.get("operation") or "write"),
            before=StateSnapshot.from_dict(before_payload) if before_payload else None,
            after=StateSnapshot.from_dict(payload["after"]),
            metadata=dict(payload.get("metadata") or {}),
        )


@dataclass(frozen=True)
class ConsistencyIssue:
    code: str
    message: str
    severity: str = "error"
    details: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "severity": self.severity,
            "details": to_jsonable(self.details),
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ConsistencyIssue":
        return cls(
            code=str(payload["code"]),
            message=str(payload["message"]),
            severity=str(payload.get("severity") or "error"),
            details=dict(payload.get("details") or {}),
            created_at=str(payload.get("created_at") or utc_now_iso()),
        )


@dataclass(frozen=True)
class OutcomeResult:
    name: str
    passed: bool
    reason: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    checked_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "reason": self.reason,
            "details": to_jsonable(self.details),
            "checked_at": self.checked_at,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "OutcomeResult":
        return cls(
            name=str(payload["name"]),
            passed=bool(payload["passed"]),
            reason=str(payload.get("reason") or ""),
            details=dict(payload.get("details") or {}),
            checked_at=str(payload.get("checked_at") or utc_now_iso()),
        )


@dataclass(frozen=True)
class ProofArtifact:
    name: str
    kind: str
    digest: str
    verified: bool = False
    uri: Optional[str] = None
    verifier: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now_iso)
    value: Optional[Any] = field(default=None, repr=False, compare=False)

    @property
    def artifact_id(self) -> str:
        return f"{self.kind}:{self.name}:{self.digest[:16]}"

    @classmethod
    def capture(
        cls,
        name: str,
        value: Any,
        *,
        kind: str = "data",
        verified: bool = False,
        uri: Optional[str] = None,
        verifier: Optional[str] = None,
        details: Optional[Mapping[str, Any]] = None,
        include_value: bool = False,
    ) -> "ProofArtifact":
        return cls(
            name=name,
            kind=kind,
            digest=stable_digest(value),
            verified=verified,
            uri=uri,
            verifier=verifier,
            details=dict(details or {}),
            value=to_jsonable(value) if include_value else None,
        )

    def to_dict(self) -> Dict[str, Any]:
        payload = {
            "artifact_id": self.artifact_id,
            "name": self.name,
            "kind": self.kind,
            "digest": self.digest,
            "verified": self.verified,
            "uri": self.uri,
            "verifier": self.verifier,
            "details": to_jsonable(self.details),
            "created_at": self.created_at,
        }
        if self.value is not None:
            payload["value"] = self.value
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ProofArtifact":
        return cls(
            name=str(payload["name"]),
            kind=str(payload.get("kind") or "data"),
            digest=str(payload["digest"]),
            verified=bool(payload.get("verified")),
            uri=payload.get("uri"),
            verifier=payload.get("verifier"),
            details=dict(payload.get("details") or {}),
            created_at=str(payload.get("created_at") or utc_now_iso()),
            value=payload.get("value"),
        )


@dataclass
class ConsistencyReceipt:
    run_id: str
    step_id: str
    agent: str
    action: str
    schema_version: str = RECEIPT_SCHEMA_VERSION
    receipt_id: str = ""
    previous_receipt_digest: Optional[str] = None
    receipt_digest: Optional[str] = None
    assumptions: List[str] = field(default_factory=list)
    state_reads: List[StateSnapshot] = field(default_factory=list)
    state_deltas: List[StateDelta] = field(default_factory=list)
    handoffs: List[Any] = field(default_factory=list)
    proof_artifacts: List[ProofArtifact] = field(default_factory=list)
    outcomes: List[OutcomeResult] = field(default_factory=list)
    issues: List[ConsistencyIssue] = field(default_factory=list)
    parent_receipt_keys: List[str] = field(default_factory=list)
    consumed_handoff_ids: List[str] = field(default_factory=list)
    produced_handoff_ids: List[str] = field(default_factory=list)
    consumed_artifact_ids: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    status: str = "running"
    error: Optional[Dict[str, Any]] = None
    created_at: str = field(default_factory=utc_now_iso)
    finished_at: Optional[str] = None

    @property
    def key(self) -> str:
        return f"{self.run_id}:{self.step_id}"

    def prepare_for_storage(self, *, previous_receipt_digest: Optional[str] = None) -> None:
        self.schema_version = self.schema_version or RECEIPT_SCHEMA_VERSION
        self.receipt_id = self.receipt_id or self.key
        self.previous_receipt_digest = previous_receipt_digest
        self.receipt_digest = self.compute_digest()

    def compute_digest(self) -> str:
        return compute_receipt_digest(self.to_dict(include_receipt_digest=False))

    def finish(self, *, error: Optional[BaseException] = None) -> None:
        self.finished_at = utc_now_iso()
        if error is not None:
            self.status = "failed"
            self.error = {"type": error.__class__.__name__, "message": str(error)}
            return
        failed_outcome = any(not outcome.passed for outcome in self.outcomes)
        error_issue = any(issue.severity == "error" for issue in self.issues)
        self.status = "failed" if failed_outcome or error_issue else "passed"

    def to_dict(self, *, include_receipt_digest: bool = True) -> Dict[str, Any]:
        payload = {
            "schema_version": self.schema_version or RECEIPT_SCHEMA_VERSION,
            "receipt_id": self.receipt_id or self.key,
            "run_id": self.run_id,
            "step_id": self.step_id,
            "agent": self.agent,
            "action": self.action,
            "assumptions": list(self.assumptions),
            "state_reads": [snapshot.to_dict() for snapshot in self.state_reads],
            "state_deltas": [delta.to_dict() for delta in self.state_deltas],
            "handoffs": [handoff.to_dict() for handoff in self.handoffs],
            "proof_artifacts": [artifact.to_dict() for artifact in self.proof_artifacts],
            "outcomes": [outcome.to_dict() for outcome in self.outcomes],
            "issues": [issue.to_dict() for issue in self.issues],
            "parent_receipt_keys": list(self.parent_receipt_keys),
            "consumed_handoff_ids": list(self.consumed_handoff_ids),
            "produced_handoff_ids": list(self.produced_handoff_ids),
            "consumed_artifact_ids": list(self.consumed_artifact_ids),
            "metadata": to_jsonable(self.metadata),
            "status": self.status,
            "error": to_jsonable(self.error),
            "created_at": self.created_at,
            "finished_at": self.finished_at,
            "previous_receipt_digest": self.previous_receipt_digest,
        }
        if include_receipt_digest:
            payload[RECEIPT_DIGEST_FIELD] = self.receipt_digest
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ConsistencyReceipt":
        from .handoff import HandoffPacket

        return cls(
            schema_version=str(payload.get("schema_version") or RECEIPT_SCHEMA_VERSION),
            receipt_id=str(payload.get("receipt_id") or ""),
            previous_receipt_digest=payload.get("previous_receipt_digest"),
            receipt_digest=payload.get(RECEIPT_DIGEST_FIELD),
            run_id=str(payload["run_id"]),
            step_id=str(payload["step_id"]),
            agent=str(payload["agent"]),
            action=str(payload["action"]),
            assumptions=list(payload.get("assumptions") or []),
            state_reads=[
                StateSnapshot.from_dict(item) for item in payload.get("state_reads") or []
            ],
            state_deltas=[StateDelta.from_dict(item) for item in payload.get("state_deltas") or []],
            handoffs=[HandoffPacket.from_dict(item) for item in payload.get("handoffs") or []],
            proof_artifacts=[
                ProofArtifact.from_dict(item) for item in payload.get("proof_artifacts") or []
            ],
            outcomes=[OutcomeResult.from_dict(item) for item in payload.get("outcomes") or []],
            issues=[ConsistencyIssue.from_dict(item) for item in payload.get("issues") or []],
            parent_receipt_keys=list(payload.get("parent_receipt_keys") or []),
            consumed_handoff_ids=list(payload.get("consumed_handoff_ids") or []),
            produced_handoff_ids=list(payload.get("produced_handoff_ids") or []),
            consumed_artifact_ids=list(payload.get("consumed_artifact_ids") or []),
            metadata=dict(payload.get("metadata") or {}),
            status=str(payload.get("status") or "running"),
            error=payload.get("error"),
            created_at=str(payload.get("created_at") or utc_now_iso()),
            finished_at=payload.get("finished_at"),
        )
