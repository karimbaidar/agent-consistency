from agent_consistency import JsonlReceiptStore, WorkflowRun, detect_risks, render_risk_report
from agent_consistency.cli import main
from agent_consistency.integrations import detect_workflow, run_detected_workflow


def test_detect_risks_keeps_clean_run_clean():
    run = WorkflowRun.detect("clean-run")

    with run.step("refund-agent", "issue_refund", step_id="refund") as step:
        refund = {"status": "settled"}
        step.verify_outcome("refund_settled", lambda: refund["status"] == "settled")

    with run.step("comms-agent", "email_customer", step_id="email") as step:
        step.verify_outcome("customer_message_sent", lambda: True)

    report = detect_risks(run.receipts())

    assert report.findings == []
    assert "Risk status: CLEAN" in render_risk_report(report)


def test_detect_risks_reports_stale_state():
    run = WorkflowRun.detect("stale-run")

    with run.step("policy-agent", "approve_refund", step_id="policy") as step:
        policy = step.read_state("refund_policy", {"limit": 100}, version="v12")
        step.ensure_fresh(policy, current_value={"limit": 50}, current_version="v14")

    report = detect_risks(run.receipts())

    assert _finding_types(report) >= {"stale_state_read"}
    assert report.has_high_severity is True


def test_detect_risks_reports_dropped_handoff_fact():
    run = WorkflowRun.detect("handoff-run")

    with run.step("history-agent", "handoff_order", step_id="history") as step:
        step.handoff(
            to_agent="refund-agent",
            task="decide refund eligibility",
            facts={"order": {"id": "ord_1"}},
            missing_info=["order.previous_refund_count"],
            required_facts=["order.previous_refund_count"],
        )

    report = detect_risks(run.receipts())

    assert _finding_types(report) >= {"dropped_handoff_fact"}
    assert report.ranked_findings[0].severity == "high"


def test_detect_risks_reports_customer_action_after_failed_outcome():
    run = WorkflowRun.detect("customer-risk")

    with run.step("refund-agent", "issue_refund", step_id="refund") as step:
        step.verify_outcome("refund_settled", lambda: False, failure_reason="pending")

    with run.step("comms-agent", "email_customer", step_id="email") as step:
        step.write_state("message", {"body": "your refund is complete"})

    report = detect_risks(run.receipts())

    assert _finding_types(report) >= {"customer_action_after_unverified_outcome"}
    assert report.has_high_severity is True


def test_detect_cli_exits_nonzero_on_high_risk(tmp_path, capsys):
    path = tmp_path / "receipts.jsonl"
    store = JsonlReceiptStore(str(path))
    run = WorkflowRun.detect("cli-risk", store=store)

    with run.step("refund-agent", "issue_refund", step_id="refund") as step:
        step.verify_outcome("refund_settled", lambda: False, failure_reason="pending")

    code = main(["detect", str(path)])
    output = capsys.readouterr().out

    assert code == 1
    assert "Risk status: HIGH RISK" in output
    assert "failed_outcome" in output


def test_detect_workflow_one_call_returns_report():
    def workflow(run):
        with run.step("agent", "issue_refund", step_id="refund") as step:
            step.verify_outcome("refund_settled", lambda: False)

    report = detect_workflow(workflow, run_id="one-call")

    assert report.run_id == "one-call"
    assert report.has_high_severity is True


def test_run_detected_workflow_returns_result_and_report():
    def workflow(run):
        with run.step("agent", "act", step_id="step") as step:
            step.verify_outcome("done", lambda: True)
        return "ok"

    result, report = run_detected_workflow(workflow, run_id="tuple-call")

    assert result == "ok"
    assert report.findings == []


def _finding_types(report):
    return {finding.finding_type for finding in report.findings}
