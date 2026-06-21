import json

from agent_consistency import (
    JsonlReceiptStore,
    WorkflowRun,
    render_verify_report,
    verify_receipt_file,
)
from agent_consistency.cli import main
from agent_consistency.serialization import stable_json


def test_verify_reports_passed_run_with_verified_integrity(tmp_path, capsys):
    path = tmp_path / "receipts.jsonl"
    store = JsonlReceiptStore(str(path))
    run = WorkflowRun("verify-pass", store=store)

    with run.step("agent", "act", step_id="step-1") as step:
        step.read_state("state", {"value": 1}, version="1")

    code = main(["verify", str(path)])
    output = capsys.readouterr().out

    assert code == 0
    assert "Integrity: verified" in output
    assert "Run status: passed" in output
    assert "Digest chain: verified" in output


def test_verify_reports_failed_run_as_expected_without_nonzero_exit(tmp_path, capsys):
    path = tmp_path / "receipts.jsonl"
    store = JsonlReceiptStore(str(path))
    run = WorkflowRun("verify-pending", store=store, on_violation="record")

    with run.step("refund-agent", "issue_refund", step_id="refund") as step:
        provider_result = {"refund_id": "rf_1", "status": "pending"}
        step.verify_outcome(
            "refund_settled",
            lambda: provider_result["status"] == "settled",
            failure_reason="refund status is pending, not settled",
            details=provider_result,
        )

    code = main(["verify", str(path)])
    output = capsys.readouterr().out

    assert code == 0
    assert "Integrity: verified" in output
    assert "Run status: failed as expected" in output
    assert "outcome refund_settled failed" in output


def test_verify_fails_when_receipt_is_tampered(tmp_path):
    path = tmp_path / "receipts.jsonl"
    store = JsonlReceiptStore(str(path))
    run = WorkflowRun("tamper-run", store=store)

    with run.step("agent", "act", step_id="step-1"):
        pass

    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["action"] = "changed_after_write"
    path.write_text(stable_json(payload) + "\n", encoding="utf-8")

    report = verify_receipt_file(str(path))
    rendered = render_verify_report(report)

    assert report.ok is False
    assert "digest mismatch" in rendered
    assert "tamper-run:step-1" in rendered


def test_verify_fails_when_receipts_are_reordered(tmp_path):
    path = tmp_path / "receipts.jsonl"
    store = JsonlReceiptStore(str(path))
    run = WorkflowRun("reorder-run", store=store)

    with run.step("agent", "first", step_id="step-1"):
        pass
    with run.step("agent", "second", step_id="step-2"):
        pass

    lines = path.read_text(encoding="utf-8").splitlines()
    path.write_text("\n".join(reversed(lines)) + "\n", encoding="utf-8")

    report = verify_receipt_file(str(path))
    rendered = render_verify_report(report)

    assert report.ok is False
    assert "previous digest mismatch" in rendered


def test_verify_fails_for_missing_required_field(tmp_path):
    path = tmp_path / "receipts.jsonl"
    path.write_text(
        stable_json(
            {
                "run_id": "missing-field",
                "step_id": "step-1",
                "agent": "agent",
                "status": "passed",
                "created_at": "2026-01-01T00:00:00Z",
                "finished_at": "2026-01-01T00:00:01Z",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    report = verify_receipt_file(str(path))
    rendered = render_verify_report(report)

    assert report.ok is False
    assert "missing required field 'action'" in rendered


def test_verify_fails_for_malformed_jsonl(tmp_path):
    path = tmp_path / "receipts.jsonl"
    path.write_text("{not-json}\n", encoding="utf-8")

    report = verify_receipt_file(str(path))
    rendered = render_verify_report(report)

    assert report.ok is False
    assert "invalid JSON" in rendered


def test_verify_fails_for_unresolved_handoff_reference(tmp_path):
    path = tmp_path / "receipts.jsonl"
    path.write_text(
        stable_json(
            {
                "run_id": "bad-ref",
                "step_id": "step-1",
                "agent": "agent",
                "action": "act",
                "status": "passed",
                "created_at": "2026-01-01T00:00:00Z",
                "finished_at": "2026-01-01T00:00:01Z",
                "consumed_handoff_ids": ["handoff:missing"],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    report = verify_receipt_file(str(path))
    rendered = render_verify_report(report)

    assert report.ok is False
    assert "consumed handoff reference does not resolve" in rendered


def test_schema_cli_prints_receipt_schema(capsys):
    code = main(["schema"])
    output = capsys.readouterr().out

    assert code == 0
    assert '"title": "agent-consistency receipt"' in output
    assert '"receipt_digest"' in output
