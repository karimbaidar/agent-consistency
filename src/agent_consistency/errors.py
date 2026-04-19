from typing import Any, Dict, Optional


class ConsistencyError(Exception):
    """Base error for agent workflow consistency violations."""


class StaleStateError(ConsistencyError):
    def __init__(
        self,
        message: str,
        *,
        snapshot: Optional[Any] = None,
        current: Optional[Any] = None,
    ) -> None:
        super().__init__(message)
        self.snapshot = snapshot
        self.current = current


class HandoffValidationError(ConsistencyError):
    def __init__(self, message: str, *, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.details = details or {}


class OutcomeVerificationError(ConsistencyError):
    def __init__(self, message: str, *, result: Optional[Any] = None) -> None:
        super().__init__(message)
        self.result = result


class DuplicateReceiptError(ConsistencyError):
    def __init__(self, message: str, *, receipt_key: Optional[str] = None) -> None:
        super().__init__(message)
        self.receipt_key = receipt_key
