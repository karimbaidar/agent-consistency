from agent_consistency import JsonlReceiptStore, WorkflowRun
from agent_consistency.cli import main
from agent_consistency.reporting import load_receipt_report, summarize_report


def test_reporting_summarizes_jsonl_receipts(tmp_path):
    path = tmp_path / "receipts.jsonl"
    store = JsonlReceiptStore(str(path))
    run = WorkflowRun("report-run", store=store, on_violation="record")

    with run.step("refund-agent", "issue_refund", step_id="refund") as step:
        step.verify_outcome("refund_settled", lambda: False, failure_reason="pending")

    report = load_receipt_report(str(path))
    summary = summarize_report(report)

    assert summary["run_id"] == "report-run"
    assert summary["status"] == "failed"
    assert summary["issue_count"] == 1
    assert summary["outcomes"][0]["name"] == "refund_settled"


def test_report_cli_prints_text_and_writes_html(tmp_path, capsys):
    path = tmp_path / "receipts.jsonl"
    html_path = tmp_path / "report.html"
    store = JsonlReceiptStore(str(path))
    run = WorkflowRun("cli-run", store=store)

    with run.step("agent", "act", step_id="step-1") as step:
        step.read_state("state", {"value": 1}, version="1")

    code = main(["report", str(path), "--html", str(html_path)])
    output = capsys.readouterr().out

    assert code == 0
    assert "Run: cli-run" in output
    assert "Status: PASSED" in output
    assert "HTML report:" in output
    assert html_path.exists()
