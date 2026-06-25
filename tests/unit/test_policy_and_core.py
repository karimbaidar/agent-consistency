import os
import time

import pytest

from agent_consistency import (
    BufferedReceiptStore,
    FailurePolicy,
    InMemoryReceiptStore,
    OutcomeVerificationError,
    RefundSettlementVerifier,
    WorkflowRun,
)


def test_low_criticality_failure_records_fail_open_without_raising():
    run = WorkflowRun("fail-open-run")

    with pytest.warns(RuntimeWarning):
        with run.step("agent", "observe", step_id="step", criticality="low") as step:
            result = step.verify_outcome("cache_warmed", lambda: False)

    [receipt] = run.receipts()
    assert result.passed is False
    assert receipt.status == "failed"
    assert receipt.issues[0].severity == "warning"
    assert receipt.policy_decisions[0]["mode"] == "fail_open"


def test_financial_failure_defaults_fail_closed():
    run = WorkflowRun("fail-closed-run")

    with pytest.raises(OutcomeVerificationError):
        with run.step(
            "refund-agent",
            "issue_refund",
            step_id="refund",
            criticality="financial",
        ) as step:
            step.verify_outcome("refund_settled", lambda: False)

    [receipt] = run.receipts()
    assert receipt.status == "failed"
    assert receipt.policy_decisions[0]["mode"] == "fail_closed"
    assert receipt.policy_decisions[0]["criticality"] == "financial"


def test_policy_can_configure_medium_fail_open():
    run = WorkflowRun(
        "custom-policy-run",
        failure_policy=FailurePolicy(by_criticality={"medium": "fail_open"}),
    )

    with pytest.warns(RuntimeWarning):
        with run.step("agent", "medium_check", step_id="step", criticality="medium") as step:
            step.verify_outcome("noncritical_report", lambda: False)

    [receipt] = run.receipts()
    assert receipt.policy_decisions[0]["mode"] == "fail_open"


def test_duplicate_idempotency_key_refuses_second_fire():
    run = WorkflowRun("idempotency-run")

    with run.step(
        "refund-agent",
        "issue_refund",
        step_id="first",
        idempotency_key="refund:ord_1",
    ):
        pass

    with pytest.raises(OutcomeVerificationError):
        with run.step(
            "refund-agent",
            "issue_refund",
            step_id="second",
            idempotency_key="refund:ord_1",
        ):
            pass

    first, second = run.receipts()
    assert first.idempotency_key == "refund:ord_1"
    assert second.status == "failed"
    assert second.issues[0].code == "duplicate_idempotency_key"


def test_refund_settlement_verifier_checks_provider_ground_truth():
    provider = {
        "rf_settled": {"status": "settled", "provider": "fake-pay"},
        "rf_pending": {"status": "pending", "provider": "fake-pay"},
    }

    passed = RefundSettlementVerifier("rf_settled", provider.__getitem__).run()
    failed = RefundSettlementVerifier("rf_pending", provider.__getitem__).run()

    assert passed.passed is True
    assert passed.details["provider"] == "fake-pay"
    assert failed.passed is False
    assert "pending" in failed.reason


def test_verifier_errors_resolve_through_policy():
    run = WorkflowRun("verifier-error")

    def provider_status(refund_id: str) -> dict:
        raise TimeoutError(f"provider timed out for {refund_id}")

    with pytest.raises(OutcomeVerificationError):
        with run.step("refund-agent", "issue_refund", step_id="refund") as step:
            step.verify_outcome_with(RefundSettlementVerifier("rf_1", provider_status))

    [receipt] = run.receipts()
    assert receipt.outcomes[0].passed is False
    assert receipt.outcomes[0].details["error_type"] == "TimeoutError"
    assert receipt.policy_decisions[0]["mode"] == "fail_closed"


def test_buffered_store_flushes_failed_receipts():
    target = InMemoryReceiptStore()
    run = WorkflowRun("buffered-run", store=BufferedReceiptStore(target))

    with pytest.raises(OutcomeVerificationError):
        with run.step("refund-agent", "issue_refund", step_id="refund") as step:
            step.verify_outcome("refund_settled", lambda: False)

    [receipt] = target.list(run_id="buffered-run")
    assert receipt.status == "failed"
    assert receipt.receipt_digest


@pytest.mark.performance
def test_contract_checks_stay_cheap_smoke():
    if os.environ.get("AGENT_CONSISTENCY_SKIP_PERF") == "1":
        pytest.skip("performance smoke skipped in constrained environment")

    start = time.perf_counter()
    run = WorkflowRun("perf-run", on_violation="record")
    for index in range(1000):
        with run.step("agent", "read", step_id=f"step-{index}") as step:
            snapshot = step.read_state("policy", {"version": index}, version=str(index))
            step.ensure_fresh(snapshot, current_version=str(index))
    elapsed = time.perf_counter() - start

    assert elapsed < 1.0
