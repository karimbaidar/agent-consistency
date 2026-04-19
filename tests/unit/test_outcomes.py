import pytest

from agent_consistency import OutcomeVerificationError, WorkflowRun, verify_outcome


def test_standalone_outcome_verifier_returns_result():
    result = verify_outcome("ticket_exists", lambda: True)

    assert result.name == "ticket_exists"
    assert result.passed is True
    assert result.reason == "postcondition passed"


def test_failed_outcome_is_recorded_before_raise():
    run = WorkflowRun("outcome-run")

    with pytest.raises(OutcomeVerificationError):
        with run.step("refund-agent", "issue_refund", step_id="refund") as step:
            step.verify_outcome(
                "refund_settled",
                lambda: False,
                failure_reason="refund status is pending, not settled",
            )

    [receipt] = run.receipts()
    assert receipt.status == "failed"
    assert receipt.outcomes[0].passed is False
    assert "pending" in receipt.outcomes[0].reason


def test_record_mode_captures_failed_outcome_without_raising():
    run = WorkflowRun("record-run", on_violation="record")

    with run.step("refund-agent", "issue_refund", step_id="refund") as step:
        result = step.verify_outcome("refund_settled", lambda: False)

    [receipt] = run.receipts()
    assert result.passed is False
    assert receipt.status == "failed"
    assert receipt.issues[0].code == "outcome_failed"
