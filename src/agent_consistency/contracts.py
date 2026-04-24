from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional

from .models import ProofArtifact
from .serialization import to_jsonable


@dataclass(frozen=True)
class HandoffContract:
    name: str
    required_facts: List[str] = field(default_factory=list)
    required_evidence: List[str] = field(default_factory=list)
    required_assumptions: List[str] = field(default_factory=list)
    required_constraints: List[str] = field(default_factory=list)
    produced_artifacts: List[str] = field(default_factory=list)
    verifier: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def define(
        cls,
        name: str,
        *,
        required_facts: Optional[Iterable[str]] = None,
        required_evidence: Optional[Iterable[str]] = None,
        required_assumptions: Optional[Iterable[str]] = None,
        required_constraints: Optional[Iterable[str]] = None,
        produced_artifacts: Optional[Iterable[str]] = None,
        verifier: Optional[str] = None,
        metadata: Optional[Mapping[str, Any]] = None,
    ) -> "HandoffContract":
        return cls(
            name=name,
            required_facts=list(required_facts or []),
            required_evidence=list(required_evidence or []),
            required_assumptions=list(required_assumptions or []),
            required_constraints=list(required_constraints or []),
            produced_artifacts=list(produced_artifacts or []),
            verifier=verifier,
            metadata=dict(metadata or {}),
        )

    def validate_artifacts(self, artifacts: Iterable[ProofArtifact]) -> List[str]:
        by_name = {artifact.name: artifact for artifact in artifacts}
        problems: List[str] = []
        for name in self.produced_artifacts:
            artifact = by_name.get(name)
            if artifact is None:
                problems.append(f"required artifact '{name}' is missing")
            elif not artifact.verified:
                problems.append(f"required artifact '{name}' is not verified")
        return problems

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "required_facts": list(self.required_facts),
            "required_evidence": list(self.required_evidence),
            "required_assumptions": list(self.required_assumptions),
            "required_constraints": list(self.required_constraints),
            "produced_artifacts": list(self.produced_artifacts),
            "verifier": self.verifier,
            "metadata": to_jsonable(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "HandoffContract":
        return cls(
            name=str(payload["name"]),
            required_facts=list(payload.get("required_facts") or []),
            required_evidence=list(payload.get("required_evidence") or []),
            required_assumptions=list(payload.get("required_assumptions") or []),
            required_constraints=list(payload.get("required_constraints") or []),
            produced_artifacts=list(payload.get("produced_artifacts") or []),
            verifier=payload.get("verifier"),
            metadata=dict(payload.get("metadata") or {}),
        )
