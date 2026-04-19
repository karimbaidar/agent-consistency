from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ._time import utc_now_iso
from .serialization import stable_digest, to_jsonable


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


@dataclass
class ConsistencyReceipt:
    run_id: str
    step_id: str
    agent: str
    action: str
    assumptions: List[str] = field(default_factory=list)
    state_reads: List[StateSnapshot] = field(default_factory=list)
    state_deltas: List[StateDelta] = field(default_factory=list)
    handoffs: List[Any] = field(default_factory=list)
    outcomes: List[OutcomeResult] = field(default_factory=list)
    issues: List[ConsistencyIssue] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    status: str = "running"
    error: Optional[Dict[str, Any]] = None
    created_at: str = field(default_factory=utc_now_iso)
    finished_at: Optional[str] = None

    @property
    def key(self) -> str:
        return f"{self.run_id}:{self.step_id}"

    def finish(self, *, error: Optional[BaseException] = None) -> None:
        self.finished_at = utc_now_iso()
        if error is not None:
            self.status = "failed"
            self.error = {"type": error.__class__.__name__, "message": str(error)}
            return
        failed_outcome = any(not outcome.passed for outcome in self.outcomes)
        error_issue = any(issue.severity == "error" for issue in self.issues)
        self.status = "failed" if failed_outcome or error_issue else "passed"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "step_id": self.step_id,
            "agent": self.agent,
            "action": self.action,
            "assumptions": list(self.assumptions),
            "state_reads": [snapshot.to_dict() for snapshot in self.state_reads],
            "state_deltas": [delta.to_dict() for delta in self.state_deltas],
            "handoffs": [handoff.to_dict() for handoff in self.handoffs],
            "outcomes": [outcome.to_dict() for outcome in self.outcomes],
            "issues": [issue.to_dict() for issue in self.issues],
            "metadata": to_jsonable(self.metadata),
            "status": self.status,
            "error": to_jsonable(self.error),
            "created_at": self.created_at,
            "finished_at": self.finished_at,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ConsistencyReceipt":
        from .handoff import HandoffPacket

        return cls(
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
            outcomes=[OutcomeResult.from_dict(item) for item in payload.get("outcomes") or []],
            issues=[ConsistencyIssue.from_dict(item) for item in payload.get("issues") or []],
            metadata=dict(payload.get("metadata") or {}),
            status=str(payload.get("status") or "running"),
            error=payload.get("error"),
            created_at=str(payload.get("created_at") or utc_now_iso()),
            finished_at=payload.get("finished_at"),
        )
