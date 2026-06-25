import json
from collections.abc import Iterable
from pathlib import Path
from threading import Lock
from typing import Any, List, Optional, Protocol, Set

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
            previous_digest = self._receipts[-1].receipt_digest if self._receipts else None
            receipt.prepare_for_storage(previous_receipt_digest=previous_digest)
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
            existing = self.list()
            if self.dedupe:
                existing_keys = {
                    stored.key for stored in existing if stored.run_id == receipt.run_id
                }
                if receipt.key in existing_keys:
                    raise DuplicateReceiptError(
                        f"receipt already exists for {receipt.key}",
                        receipt_key=receipt.key,
                    )
            previous_digest = existing[-1].receipt_digest if existing else None
            receipt.prepare_for_storage(previous_receipt_digest=previous_digest)
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


class BufferedReceiptStore:
    """Buffer receipt writes and flush them to a backing store on demand."""

    def __init__(self, target: ReceiptStore, *, max_buffer_size: int = 100) -> None:
        self.target = target
        self.max_buffer_size = max_buffer_size
        self._buffer: List[ConsistencyReceipt] = []
        self._lock = Lock()

    def add(self, receipt: ConsistencyReceipt) -> None:
        should_flush = False
        with self._lock:
            self._buffer.append(receipt)
            should_flush = len(self._buffer) >= self.max_buffer_size
        if should_flush:
            self.flush()

    def flush(self) -> None:
        with self._lock:
            pending = list(self._buffer)
            self._buffer.clear()
        for receipt in pending:
            self.target.add(receipt)

    def list(self, *, run_id: Optional[str] = None) -> List[ConsistencyReceipt]:
        receipts = self.target.list(run_id=run_id)
        with self._lock:
            pending = list(self._buffer)
        if run_id is not None:
            pending = [receipt for receipt in pending if receipt.run_id == run_id]
        return receipts + pending


class PostgresReceiptStore:
    """DB-API receipt store for psycopg-style PostgreSQL connections."""

    def __init__(self, connection: Any, *, table_name: str = "agent_consistency_receipts") -> None:
        self.connection = connection
        self.table_name = table_name
        self._ensure_table()

    def _ensure_table(self) -> None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"""
                create table if not exists {self.table_name} (
                    receipt_key text primary key,
                    run_id text not null,
                    payload jsonb not null
                )
                """
            )
        self.connection.commit()

    def add(self, receipt: ConsistencyReceipt) -> None:
        existing = self.list(run_id=receipt.run_id)
        previous_digest = existing[-1].receipt_digest if existing else None
        receipt.prepare_for_storage(previous_receipt_digest=previous_digest)
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"""
                insert into {self.table_name} (receipt_key, run_id, payload)
                values (%s, %s, %s)
                """,
                (receipt.key, receipt.run_id, stable_json(receipt.to_dict())),
            )
        self.connection.commit()

    def list(self, *, run_id: Optional[str] = None) -> List[ConsistencyReceipt]:
        query = f"select payload from {self.table_name}"
        params: tuple[str, ...] = ()
        if run_id is not None:
            query += " where run_id = %s"
            params = (run_id,)
        query += " order by receipt_key"
        receipts: List[ConsistencyReceipt] = []
        with self.connection.cursor() as cursor:
            cursor.execute(query, params)
            for (payload,) in cursor.fetchall():
                if isinstance(payload, str):
                    payload = json.loads(payload)
                receipts.append(ConsistencyReceipt.from_dict(payload))
        return receipts


class OtelReceiptExporter:
    """Export receipts as OpenTelemetry spans when the optional extra is installed."""

    def __init__(self, tracer_name: str = "agent_consistency.receipts") -> None:
        try:
            from opentelemetry import trace
        except ImportError as exc:  # pragma: no cover - depends on optional extra
            message = "install agent-consistency[otel] to use OtelReceiptExporter"
            raise RuntimeError(message) from exc
        self.tracer = trace.get_tracer(tracer_name)

    def add(self, receipt: ConsistencyReceipt) -> None:
        with self.tracer.start_as_current_span(
            "agent_consistency.receipt",
            attributes=self._attributes(receipt),
        ):
            return

    def list(self, *, run_id: Optional[str] = None) -> List[ConsistencyReceipt]:
        return []

    def _attributes(self, receipt: ConsistencyReceipt) -> dict[str, Any]:
        latest_policy = receipt.policy_decisions[-1] if receipt.policy_decisions else {}
        return {
            "gen_ai.operation.name": receipt.action,
            "gen_ai.system": "agent-consistency",
            "agent_consistency.run_id": receipt.run_id,
            "agent_consistency.step_id": receipt.step_id,
            "agent_consistency.agent": receipt.agent,
            "agent_consistency.action": receipt.action,
            "agent_consistency.status": receipt.status,
            "agent_consistency.criticality": receipt.metadata.get("criticality", ""),
            "agent_consistency.policy.mode": latest_policy.get("mode", ""),
        }


def load_receipts(receipts: Iterable[ConsistencyReceipt]) -> InMemoryReceiptStore:
    store = InMemoryReceiptStore(dedupe=False)
    for receipt in receipts:
        store.add(receipt)
    return store
