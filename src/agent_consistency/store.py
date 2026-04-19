import json
from collections.abc import Iterable
from pathlib import Path
from threading import Lock
from typing import List, Optional, Protocol, Set

from .errors import DuplicateReceiptError
from .models import ConsistencyReceipt
from .serialization import stable_json


class ReceiptStore(Protocol):
    def add(self, receipt: ConsistencyReceipt) -> None:
        ...

    def list(self, *, run_id: Optional[str] = None) -> List[ConsistencyReceipt]:
        ...


class InMemoryReceiptStore:
    def __init__(self, *, dedupe: bool = True) -> None:
        self.dedupe = dedupe
        self._receipts: List[ConsistencyReceipt] = []
        self._keys: Set[str] = set()
        self._lock = Lock()

    def add(self, receipt: ConsistencyReceipt) -> None:
        with self._lock:
            if self.dedupe and receipt.key in self._keys:
                raise DuplicateReceiptError(
                    f"receipt already exists for {receipt.key}",
                    receipt_key=receipt.key,
                )
            self._receipts.append(receipt)
            self._keys.add(receipt.key)

    def list(self, *, run_id: Optional[str] = None) -> List[ConsistencyReceipt]:
        with self._lock:
            receipts = list(self._receipts)
        if run_id is None:
            return receipts
        return [receipt for receipt in receipts if receipt.run_id == run_id]


class JsonlReceiptStore:
    def __init__(self, path: str, *, dedupe: bool = True) -> None:
        self.path = Path(path)
        self.dedupe = dedupe
        self._lock = Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def add(self, receipt: ConsistencyReceipt) -> None:
        with self._lock:
            if self.dedupe:
                existing_keys = {stored.key for stored in self.list(run_id=receipt.run_id)}
                if receipt.key in existing_keys:
                    raise DuplicateReceiptError(
                        f"receipt already exists for {receipt.key}",
                        receipt_key=receipt.key,
                    )
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(stable_json(receipt.to_dict()) + "\n")

    def list(self, *, run_id: Optional[str] = None) -> List[ConsistencyReceipt]:
        if not self.path.exists():
            return []
        receipts: List[ConsistencyReceipt] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    receipt = ConsistencyReceipt.from_dict(json.loads(line))
                    if run_id is None or receipt.run_id == run_id:
                        receipts.append(receipt)
        return receipts


def load_receipts(receipts: Iterable[ConsistencyReceipt]) -> InMemoryReceiptStore:
    store = InMemoryReceiptStore(dedupe=False)
    for receipt in receipts:
        store.add(receipt)
    return store
