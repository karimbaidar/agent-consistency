from dataclasses import dataclass
from typing import Dict, Literal, Mapping, Optional

Criticality = Literal["low", "medium", "high", "irreversible", "financial"]
FailureMode = Literal["fail_open", "fail_closed"]


@dataclass(frozen=True)
class PolicyDecision:
    criticality: str
    mode: FailureMode
    reason: str

    @property
    def blocks(self) -> bool:
        return self.mode == "fail_closed"

    def to_dict(self) -> Dict[str, str]:
        return {
            "criticality": self.criticality,
            "mode": self.mode,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, str]) -> "PolicyDecision":
        mode = str(payload.get("mode") or "fail_closed")
        if mode not in {"fail_open", "fail_closed"}:
            mode = "fail_closed"
        return cls(
            criticality=str(payload.get("criticality") or "high"),
            mode=mode,  # type: ignore[arg-type]
            reason=str(payload.get("reason") or "policy decision"),
        )


class FailurePolicy:
    """Resolve whether a failed or errored gate should block continuation."""

    def __init__(
        self,
        *,
        default_mode: FailureMode = "fail_closed",
        by_criticality: Optional[Mapping[str, FailureMode]] = None,
    ) -> None:
        self.default_mode = default_mode
        self.by_criticality: Dict[str, FailureMode] = {
            "low": "fail_open",
            "medium": default_mode,
            "high": "fail_closed",
            "irreversible": "fail_closed",
            "financial": "fail_closed",
        }
        if by_criticality:
            self.by_criticality.update(dict(by_criticality))

    def resolve(
        self,
        criticality: str,
        *,
        reason: str = "gate failed",
        error: Optional[BaseException] = None,
    ) -> PolicyDecision:
        mode = self.by_criticality.get(criticality, self.default_mode)
        if criticality in {"irreversible", "financial"}:
            mode = "fail_closed"
        if error is not None:
            reason = f"{reason}: {error.__class__.__name__}: {error}"
        return PolicyDecision(criticality=criticality, mode=mode, reason=reason)


DEFAULT_FAILURE_POLICY = FailurePolicy()

