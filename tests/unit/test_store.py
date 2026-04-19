from agent_consistency import JsonlReceiptStore, WorkflowRun


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
