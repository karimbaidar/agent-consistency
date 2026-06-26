from importlib import resources

from agent_consistency.lab import build_lab_response, scan_built_in_scenario


def test_lab_builtin_scenario_returns_report_card_and_markdown():
    report = scan_built_in_scenario()
    payload = build_lab_response(report)

    assert payload["card"]["risky_actions_found"] >= 1
    assert payload["card"]["high_severity"] >= 1
    assert payload["card"]["false_success_exposure"] >= 1
    assert payload["card"]["top_finding"]["action"] == "send_refund_confirmation"
    assert payload["card"]["gate_label"] == "BLOCK"
    assert payload["markdown"].startswith("# False-success report card")


def test_lab_static_bundle_is_packaged():
    index = resources.files("agent_consistency").joinpath("lab_static").joinpath("index.html")

    assert index.is_file()
