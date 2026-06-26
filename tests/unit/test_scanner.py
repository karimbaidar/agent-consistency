import json
from pathlib import Path

from agent_consistency.cli import main
from agent_consistency.scanner import (
    render_scan_markdown,
    scan_report_to_json,
    scan_target,
    write_baseline,
)

FIXTURES = Path(__file__).parents[1] / "fixtures" / "scanner"


def test_scan_reports_refund_missing_confirmation():
    report = scan_target(str(FIXTURES / "refund_missing_confirmation"))
    finding = report.ranked_findings[0]

    assert report.risky_actions_found == 1
    assert report.high_severity == 1
    assert finding.action == "send_refund_confirmation"
    assert finding.severity == "high"
    assert finding.confidence in {"high", "medium"}
    assert finding.line > 0
    assert "confirmed outcome check" in finding.evidence_missing


def test_scan_does_not_flag_verified_refund_action():
    report = scan_target(str(FIXTURES / "refund_verified"))

    assert report.findings == []
    assert report.verified_actions_found >= 1


def test_scan_reports_delete_user_idempotency_gap():
    report = scan_target(str(FIXTURES / "delete_user_missing_idempotency"))
    finding = report.ranked_findings[0]

    assert finding.severity == "high"
    assert finding.confidence in {"high", "medium"}
    assert report.idempotency_gaps == 1
    assert "idempotency key" in finding.evidence_missing


def test_scan_classifies_ticket_access_and_trade_as_high():
    for name in (
        "ticket_close_missing_resolution",
        "access_grant_wrong_user",
        "trade_submitted_not_filled",
    ):
        report = scan_target(str(FIXTURES / name))
        assert report.high_severity >= 1
        assert all(finding.confidence for finding in report.findings)


def test_scan_json_output_is_stable():
    report = scan_target(str(FIXTURES / "refund_missing_confirmation"))
    payload = json.loads(scan_report_to_json(report))

    assert payload["risky_actions_found"] == 1
    assert payload["finding_groups"][0]["count"] == 1
    assert payload["applicability"] in {"workflow-adjacent", "general-code"}
    assert payload["findings"][0]["fingerprint"]
    assert "generated_at" not in payload


def test_scan_markdown_output_is_shareable():
    report = scan_target(str(FIXTURES / "refund_missing_confirmation"))
    markdown = render_scan_markdown(report)

    assert markdown.startswith("# False-success report card")
    assert "## High-risk findings" in markdown
    assert "Suggested fix:" in markdown
    assert "```python" in markdown


def test_scan_exposes_system_map_and_missing_confirmation():
    report = scan_target(str(FIXTURES / "refund_missing_confirmation"))
    finding = report.ranked_findings[0]

    # Per-finding: the single source-system check whose absence is the risk.
    assert finding.missing_confirmation == finding.evidence_missing[0]

    # System map is derived deterministically from scanned facts.
    system_map = report.system_map
    assert "payment/settlement provider" in system_map.source_systems
    assert finding.action in system_map.action_surfaces

    payload = report.to_dict()
    assert payload["system_map"]["source_systems"] == system_map.source_systems
    assert payload["findings"][0]["missing_confirmation"] == finding.missing_confirmation
    # Deterministic across runs.
    assert report.to_dict()["system_map"] == payload["system_map"]


def test_scan_system_map_consumes_finding_pass_for_entry_points():
    report = scan_target(str(FIXTURES / "concordiq_style_approval"))
    finding = report.ranked_findings[0]
    system_map = report.system_map

    assert finding.path == "approval.py"
    assert finding.action == "approve"
    assert finding.confidence == "medium"
    assert report.confidence == "medium"
    assert "approval.py" in system_map.entry_points
    assert "approve" in system_map.action_surfaces
    assert "production datastore / infrastructure" in system_map.source_systems


def test_scan_markdown_includes_system_map():
    report = scan_target(str(FIXTURES / "refund_missing_confirmation"))
    markdown = render_scan_markdown(report)

    assert "## System map" in markdown
    assert "Source systems to confirm:" in markdown


def test_scan_suppression_comment_hides_finding():
    report = scan_target(str(FIXTURES / "suppressed_risk"))

    assert report.findings == []


def test_scan_baseline_suppresses_existing_findings(tmp_path):
    baseline = tmp_path / "agent-consistency-baseline.json"
    report = scan_target(str(FIXTURES / "refund_missing_confirmation"))
    write_baseline(report, str(baseline))

    filtered = scan_target(
        str(FIXTURES / "refund_missing_confirmation"),
        baseline_path=str(baseline),
    )

    assert filtered.findings == []
    assert filtered.suppressed_by_baseline == 1


def test_scan_cli_fail_on_high_exits_nonzero(capsys):
    code = main(["scan", str(FIXTURES / "refund_missing_confirmation"), "--fail-on", "high"])
    output = capsys.readouterr().out

    assert code == 1
    assert "False-success report card" in output
    assert "High severity: 1" in output


def test_scan_cli_writes_baseline(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)

    code = main(["scan", str(FIXTURES / "refund_missing_confirmation"), "--write-baseline"])
    output = capsys.readouterr().out

    assert code == 0
    assert "Baseline written" in output
    assert (tmp_path / "agent-consistency-baseline.json").exists()


def test_scan_does_not_flag_everything():
    report = scan_target(str(FIXTURES / "safe_internal_notification"))

    assert report.high_severity == 0
    assert report.risky_actions_found <= 1


def test_scan_profiles_agentic_internal_routing_without_customer_claim():
    report = scan_target(str(FIXTURES / "agentic_internal_routing"))

    assert report.profile.applicability == "agentic-workflow"
    assert report.findings == []
    assert report.risky_actions_found == 0


def test_scan_groups_repeated_false_success_exposure():
    report = scan_target(str(FIXTURES / "repeated_refund_confirmations"))
    payload = report.to_dict()

    assert report.false_success_exposure == 2
    assert report.risky_actions_found == 1
    assert payload["finding_groups"][0]["count"] == 2


def test_scan_ignores_schema_and_test_copy():
    report = scan_target(str(FIXTURES / "schema_and_test_copy"))

    assert report.findings == []


def test_scan_ignores_ui_copy_and_dev_launcher_noise():
    report = scan_target(str(FIXTURES / "ui_copy_and_dev_launcher"))

    assert report.findings == []
