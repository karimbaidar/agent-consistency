from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, Mapping, Optional, Union

from .models import ConsistencyReceipt, OutcomeResult


@dataclass(frozen=True)
class VerificationContext:
    name: str
    receipt: ConsistencyReceipt
    subject: Any = None
    facts: Optional[Mapping[str, Any]] = None
    metadata: Optional[Mapping[str, Any]] = None


VerifierResult = Union[bool, OutcomeResult]
Verifier = Callable[[VerificationContext], VerifierResult]


class VerifierRegistry:
    def __init__(self) -> None:
        self._verifiers: Dict[str, Verifier] = {}

    def register(self, name: str, verifier: Optional[Verifier] = None) -> Any:
        if verifier is not None:
            self._verifiers[name] = verifier
            return verifier

        def decorator(func: Verifier) -> Verifier:
            self._verifiers[name] = func
            return func

        return decorator

    def get(self, name: str) -> Verifier:
        try:
            return self._verifiers[name]
        except KeyError as exc:
            raise KeyError(f"verifier '{name}' is not registered") from exc

    def verify(
        self,
        name: str,
        context: VerificationContext,
        *,
        success_reason: str = "verification passed",
        failure_reason: str = "verification failed",
    ) -> OutcomeResult:
        result = self.get(name)(context)
        if isinstance(result, OutcomeResult):
            return result
        return OutcomeResult(
            name=name,
            passed=bool(result),
            reason=success_reason if result else failure_reason,
            details={
                "subject": context.subject,
                "facts": dict(context.facts or {}),
                "metadata": dict(context.metadata or {}),
            },
        )


def all_of(name: str, *verifiers: Verifier) -> Verifier:
    def run(context: VerificationContext) -> OutcomeResult:
        outcomes = [_as_outcome(name, verifier(context)) for verifier in verifiers]
        failed = [outcome for outcome in outcomes if not outcome.passed]
        return OutcomeResult(
            name=name,
            passed=not failed,
            reason="all verifiers passed" if not failed else "one or more verifiers failed",
            details={"outcomes": [outcome.to_dict() for outcome in outcomes]},
        )

    return run


def any_of(name: str, *verifiers: Verifier) -> Verifier:
    def run(context: VerificationContext) -> OutcomeResult:
        outcomes = [_as_outcome(name, verifier(context)) for verifier in verifiers]
        passed = [outcome for outcome in outcomes if outcome.passed]
        return OutcomeResult(
            name=name,
            passed=bool(passed),
            reason="at least one verifier passed" if passed else "no verifier passed",
            details={"outcomes": [outcome.to_dict() for outcome in outcomes]},
        )

    return run


def choose_verifier(
    *,
    default: str,
    rules: Iterable[tuple[Callable[[VerificationContext], bool], str]],
) -> Callable[[VerificationContext], str]:
    rule_list = list(rules)

    def choose(context: VerificationContext) -> str:
        for predicate, name in rule_list:
            if predicate(context):
                return name
        return default

    return choose


def _as_outcome(name: str, result: VerifierResult) -> OutcomeResult:
    if isinstance(result, OutcomeResult):
        return result
    return OutcomeResult(
        name=name,
        passed=bool(result),
        reason="verification passed" if result else "verification failed",
    )
