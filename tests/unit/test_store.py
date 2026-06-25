from agent_consistency import (
    BufferedReceiptStore,
    InMemoryReceiptStore,
    JsonlReceiptStore,
    PostgresReceiptStore,
    WorkflowRun,
)
from agent_consistency.models import ConsistencyReceipt


def test_jsonl_store_round_trips_receipts(tmp_path):
    path = tmp_path / "receipts.jsonl"
    store = JsonlReceiptStore(str(path))
    run = WorkflowRun("jsonl-run", store=store)

    with run.step("agent", "act", step_id="step-1") as step:
        step.read_state("state", {"value": 1}, version="1")

    receipts = store.list(run_id="jsonl-run")

    assert len(receipts) == 1
    assert receipts[0].step_id == "step-1"
    assert receipts[0].state_reads[0].version == "1"
    assert receipts[0].schema_version == "1"
    assert receipts[0].receipt_id == "jsonl-run:step-1"
    assert receipts[0].previous_receipt_digest is None
    assert receipts[0].receipt_digest


def test_jsonl_store_hash_chains_receipts(tmp_path):
    path = tmp_path / "receipts.jsonl"
    store = JsonlReceiptStore(str(path))
    run = WorkflowRun("chain-run", store=store)

    with run.step("agent", "first", step_id="step-1"):
        pass
    with run.step("agent", "second", step_id="step-2"):
        pass

    first, second = store.list()

    assert first.receipt_digest
    assert second.previous_receipt_digest == first.receipt_digest
    assert second.receipt_digest != first.receipt_digest


def test_old_receipts_without_chain_fields_still_load():
    payload = {
        "run_id": "old-run",
        "step_id": "step-1",
        "agent": "agent",
        "action": "act",
        "created_at": "2026-01-01T00:00:00Z",
        "finished_at": "2026-01-01T00:00:01Z",
        "status": "passed",
    }

    receipt = ConsistencyReceipt.from_dict(payload)

    assert receipt.schema_version == "1"
    assert receipt.receipt_id == ""
    assert receipt.receipt_digest is None


def test_buffered_store_lists_pending_and_flushes():
    target = InMemoryReceiptStore()
    store = BufferedReceiptStore(target)
    run = WorkflowRun("buffer-list-run", store=store)

    with run.step("agent", "act", step_id="step-1"):
        pass

    assert store.list(run_id="buffer-list-run")[0].step_id == "step-1"
    assert target.list(run_id="buffer-list-run") == []

    store.flush()

    assert target.list(run_id="buffer-list-run")[0].receipt_digest


class FakeCursor:
    def __init__(self, connection):
        self.connection = connection
        self.rows = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, query, params=()):
        lowered = " ".join(query.lower().split())
        if lowered.startswith("create table"):
            return
        if lowered.startswith("insert into"):
            key, run_id, payload = params
            self.connection.rows[key] = (run_id, payload)
            return
        if "where run_id" in lowered:
            run_id = params[0]
            self.rows = [
                (payload,)
                for _, (stored_run_id, payload) in sorted(self.connection.rows.items())
                if stored_run_id == run_id
            ]
            return
        self.rows = [(payload,) for _, payload in sorted(self.connection.rows.values())]

    def fetchall(self):
        return self.rows


class FakeConnection:
    def __init__(self):
        self.rows = {}
        self.commits = 0

    def cursor(self):
        return FakeCursor(self)

    def commit(self):
        self.commits += 1


def test_postgres_store_round_trips_with_dbapi_connection():
    connection = FakeConnection()
    store = PostgresReceiptStore(connection)
    run = WorkflowRun("postgres-run", store=store)

    with run.step("agent", "act", step_id="step-1") as step:
        step.read_state("state", {"value": 1}, version="1")

    [receipt] = store.list(run_id="postgres-run")
    assert receipt.step_id == "step-1"
    assert receipt.receipt_digest
    assert connection.commits >= 2
