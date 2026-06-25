from collections.abc import Mapping
from typing import Any, Callable, Dict, Optional, Protocol, Union

from .models import OutcomeResult

CheckResult = Union[bool, OutcomeResult]
OutcomeCheck = Callable[[], CheckResult]


class OutcomeVerifierProtocol(Protocol):
    name: str

    def run(self) -> OutcomeResult:
        ...


class OutcomeVerifier:
    def __init__(
        self,
        name: str,
        check: OutcomeCheck,
        *,
        success_reason: str = "postcondition passed",
        failure_reason: str = "postcondition failed",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.name = name
        self.check = check
        self.success_reason = success_reason
        self.failure_reason = failure_reason
        self.details = dict(details or {})

    def run(self) -> OutcomeResult:
        try:
            result = self.check()
        except Exception as exc:  # pragma: no cover - exercised by integration behavior
            return OutcomeResult(
                name=self.name,
                passed=False,
                reason=f"{self.failure_reason}: {exc.__class__.__name__}: {exc}",
                details=self.details,
            )
        if isinstance(result, OutcomeResult):
            return result
        return OutcomeResult(
            name=self.name,
            passed=bool(result),
            reason=self.success_reason if result else self.failure_reason,
            details=self.details,
        )


def verify_outcome(
    name: str,
    check: OutcomeCheck,
    *,
    success_reason: str = "postcondition passed",
    failure_reason: str = "postcondition failed",
    details: Optional[Dict[str, Any]] = None,
) -> OutcomeResult:
    return OutcomeVerifier(
        name,
        check,
        success_reason=success_reason,
        failure_reason=failure_reason,
        details=details,
    ).run()


class RefundSettlementVerifier:
    """Verify refund settlement by re-querying provider ground truth."""

    name = "refund_settled"

    def __init__(
        self,
        refund_id: str,
        provider_status: Callable[[str], Mapping[str, Any]],
        *,
        settled_status: str = "settled",
    ) -> None:
        self.refund_id = refund_id
        self.provider_status = provider_status
        self.settled_status = settled_status

    def run(self) -> OutcomeResult:
        payload = dict(self.provider_status(self.refund_id))
        status = str(payload.get("status") or "")
        passed = status == self.settled_status
        reason = (
            f"refund {self.refund_id} is settled"
            if passed
            else f"refund {self.refund_id} status is {status or 'unknown'}, not settled"
        )
        return OutcomeResult(
            name=self.name,
            passed=passed,
            reason=reason,
            details={"refund_id": self.refund_id, **payload},
        )
