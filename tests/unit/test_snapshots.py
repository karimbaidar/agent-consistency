import pytest

from agent_consistency import (
    InMemoryReceiptStore,
    StaleStateError,
    StateSnapshot,
    WorkflowRun,
)
from agent_consistency.serialization import stable_digest


def test_stable_digest_is_independent_of_mapping_order():
    left = {"b": 2, "a": {"z": 1, "y": 2}}
    right = {"a": {"y": 2, "z": 1}, "b": 2}

    assert stable_digest(left) == stable_digest(right)


def test_snapshot_capture_uses_explicit_version_and_digest():
    snapshot = StateSnapshot.capture("policy", {"limit": 100}, version="v12")

    assert snapshot.name == "policy"
    assert snapshot.version == "v12"
    assert len(snapshot.digest) == 64
    assert snapshot.value is None


def test_state_guard_records_stale_state_issue_before_raising():
    store = InMemoryReceiptStore()
    run = WorkflowRun("refund-run", store=store)

    with pytest.raises(StaleStateError):
        with run.step("eligibility-agent", "decide", step_id="eligibility") as step:
            policy = step.read_state("refund_policy", {"limit": 100}, version="v12")
            step.write_state(
                "refund_decision",
                {"eligible": True},
                based_on=policy,
                current_version="v14",
            )

    [receipt] = store.list(run_id="refund-run")
    assert receipt.status == "failed"
    assert receipt.issues[0].code == "stale_state"
    assert "v12" in receipt.issues[0].message
    assert "v14" in receipt.issues[0].message


def test_state_guard_can_warn_instead_of_raising():
    run = WorkflowRun("warn-run", on_violation="warn")

    with pytest.warns(RuntimeWarning):
        with run.step("writer", "write", step_id="write") as step:
            snapshot = step.read_state("shared_state", {"value": 1}, version="1")
            fresh = step.ensure_fresh(snapshot, current_version="2")

    [receipt] = run.receipts()
    assert fresh is False
    assert receipt.status == "passed"
    assert receipt.issues[0].severity == "warning"
