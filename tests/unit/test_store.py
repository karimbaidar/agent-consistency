from agent_consistency import JsonlReceiptStore, WorkflowRun
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
