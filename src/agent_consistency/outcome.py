from typing import Any, Callable, Dict, Optional, Union

from .models import OutcomeResult

CheckResult = Union[bool, OutcomeResult]
OutcomeCheck = Callable[[], CheckResult]


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
