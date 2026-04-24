from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ._time import utc_now_iso
from .contracts import HandoffContract
from .models import ProofArtifact
from .serialization import stable_digest, to_jsonable


def _get_path(payload: Mapping[str, Any], path: str) -> Any:
    if path in payload:
        return payload[path]
    current: Any = payload
    for part in path.split("."):
        if not isinstance(current, Mapping) or part not in current:
            return None
        current = current[part]
    return current


def _is_blank(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}


@dataclass(frozen=True)
class HandoffPacket:
    from_agent: str
    to_agent: str
    task: str
    facts: Dict[str, Any] = field(default_factory=dict)
    assumptions: List[str] = field(default_factory=list)
    missing_info: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    evidence: Dict[str, Any] = field(default_factory=dict)
    artifacts: List[ProofArtifact] = field(default_factory=list)
    contract: Optional[HandoffContract] = None
    handoff_id: str = ""
    input_digest: str = ""
    produced_by_receipt: Optional[str] = None
    verified: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now_iso)

    def __post_init__(self) -> None:
        if not self.input_digest:
            object.__setattr__(
                self,
                "input_digest",
                stable_digest(
                    {
                        "facts": self.facts,
                        "assumptions": self.assumptions,
                        "constraints": self.constraints,
                        "evidence": self.evidence,
                        "artifacts": [artifact.to_dict() for artifact in self.artifacts],
                        "contract": self.contract.to_dict() if self.contract else None,
                    }
                ),
            )
        if not self.handoff_id:
            object.__setattr__(
                self,
                "handoff_id",
                f"handoff:{self.from_agent}:{self.to_agent}:{self.input_digest[:16]}",
            )
        if not self.verified:
            object.__setattr__(self, "verified", not self.validate())

    def validate(
        self,
        *,
        required_facts: Optional[Iterable[str]] = None,
        required_assumptions: Optional[Iterable[str]] = None,
        required_constraints: Optional[Iterable[str]] = None,
        required_evidence: Optional[Iterable[str]] = None,
    ) -> List[str]:
        problems: List[str] = []
        required_fact_list = list(required_facts or [])
        required_assumption_list = list(required_assumptions or [])
        required_constraint_list = list(required_constraints or [])
        required_evidence_list = list(required_evidence or [])
        if self.contract:
            required_fact_list.extend(self.contract.required_facts)
            required_assumption_list.extend(self.contract.required_assumptions)
            required_constraint_list.extend(self.contract.required_constraints)
            required_evidence_list.extend(self.contract.required_evidence)

        for fact in required_fact_list:
            if _is_blank(_get_path(self.facts, fact)):
                detail = "declared missing" if fact in self.missing_info else "missing"
                problems.append(f"required fact '{fact}' is {detail}")
        for assumption in required_assumption_list:
            if assumption not in self.assumptions:
                problems.append(f"required assumption '{assumption}' is missing")
        for constraint in required_constraint_list:
            if constraint not in self.constraints:
                problems.append(f"required constraint '{constraint}' is missing")
        for evidence_key in required_evidence_list:
            if _is_blank(_get_path(self.evidence, evidence_key)):
                problems.append(f"required evidence '{evidence_key}' is missing")
        if self.contract:
            problems.extend(self.contract.validate_artifacts(self.artifacts))
        return problems

    def require_supported_claims(
        self,
        claims: Mapping[str, Any],
        *,
        by: Iterable[str],
    ) -> List[str]:
        support_keys = list(by)
        missing_support = [
            key
            for key in support_keys
            if _is_blank(_get_path(self.facts, key)) and _is_blank(_get_path(self.evidence, key))
        ]
        if not claims:
            return ["claims cannot be empty when support is required"]
        if missing_support:
            return [
                "unsupported claims "
                f"{sorted(str(key) for key in claims)}; missing support keys {missing_support}"
            ]
        return []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
            "task": self.task,
            "facts": to_jsonable(self.facts),
            "assumptions": list(self.assumptions),
            "missing_info": list(self.missing_info),
            "constraints": list(self.constraints),
            "evidence": to_jsonable(self.evidence),
            "artifacts": [artifact.to_dict() for artifact in self.artifacts],
            "contract": self.contract.to_dict() if self.contract else None,
            "handoff_id": self.handoff_id,
            "input_digest": self.input_digest,
            "produced_by_receipt": self.produced_by_receipt,
            "verified": self.verified,
            "metadata": to_jsonable(self.metadata),
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "HandoffPacket":
        return cls(
            from_agent=str(payload["from_agent"]),
            to_agent=str(payload["to_agent"]),
            task=str(payload["task"]),
            facts=dict(payload.get("facts") or {}),
            assumptions=list(payload.get("assumptions") or []),
            missing_info=list(payload.get("missing_info") or []),
            constraints=list(payload.get("constraints") or []),
            evidence=dict(payload.get("evidence") or {}),
            artifacts=[
                ProofArtifact.from_dict(item) for item in payload.get("artifacts") or []
            ],
            contract=HandoffContract.from_dict(payload["contract"])
            if payload.get("contract")
            else None,
            handoff_id=str(payload.get("handoff_id") or ""),
            input_digest=str(payload.get("input_digest") or ""),
            produced_by_receipt=payload.get("produced_by_receipt"),
            verified=bool(payload.get("verified")),
            metadata=dict(payload.get("metadata") or {}),
            created_at=str(payload.get("created_at") or utc_now_iso()),
        )
