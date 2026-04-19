from agent_consistency import WorkflowRun, diff_runs


def _run_with_policy(version):
    run = WorkflowRun(f"run-{version}")
    with run.step("eligibility-agent", "decide", step_id="eligibility") as step:
        step.read_state("refund_policy", {"limit": 100}, version=version)
        step.handoff(
            to_agent="refund-agent",
            task="issue refund",
            facts={"decision": {"eligible": True}},
        )
    return run.receipts()


def test_run_diff_reports_state_and_handoff_differences():
    left = _run_with_policy("v12")
    right = _run_with_policy("v14")

    diff = diff_runs(left, right)

    assert not diff.is_empty
    assert any(item.kind == "state_read" for item in diff.differences)
    assert "state read diverged" in diff.summary()
