from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from typing import Optional

from agent_consistency import RefundSettlementVerifier, WorkflowRun


@dataclass(frozen=True)
class ScenarioResult:
    reported_success: bool
    business_success: bool
    caught_false_success: bool
    reason: str
    receipt_statuses: tuple[str, ...] = ()

    @property
    def is_false_success(self) -> bool:
        return self.reported_success and not self.business_success


@dataclass(frozen=True)
class BenchmarkCase:
    name: str
    category: str
    description: str
    raw: Callable[[], ScenarioResult]
    protected: Callable[[], ScenarioResult]


@dataclass(frozen=True)
class BenchmarkCaseResult:
    case: BenchmarkCase
    raw: ScenarioResult
    protected: ScenarioResult


def pending_refund_not_settled() -> BenchmarkCase:
    provider = {"rf_1": {"refund_id": "rf_1", "status": "pending"}}

    def raw() -> ScenarioResult:
        return ScenarioResult(
            reported_success=True,
            business_success=False,
            caught_false_success=False,
            reason="agent sent completion message while refund was pending",
        )

    def protected() -> ScenarioResult:
        run = WorkflowRun("bench-pending-refund")
        try:
            with run.step(
                "refund-agent",
                "issue_refund",
                step_id="refund",
                criticality="financial",
            ) as step:
                step.verify_outcome_with(
                    RefundSettlementVerifier("rf_1", provider.__getitem__),
                    criticality="financial",
                )
        except Exception as exc:
            return _caught(run, str(exc))
        return _missed(run, "refund pending was not blocked")

    return BenchmarkCase(
        name="pending_refund_not_settled",
        category="outcome_verification",
        description="refund API returns but provider status remains pending",
        raw=raw,
        protected=protected,
    )


def stale_policy_snapshot() -> BenchmarkCase:
    policy_v12 = {"version": "policy-v12", "max_refund": 100}

    def raw() -> ScenarioResult:
        return ScenarioResult(
            reported_success=True,
            business_success=False,
            caught_false_success=False,
            reason="agent approved from stale policy v12 while v14 was current",
        )

    def protected() -> ScenarioResult:
        run = WorkflowRun("bench-stale-policy")
        try:
            with run.step("eligibility-agent", "approve_refund", step_id="eligibility") as step:
                snapshot = step.read_state("refund_policy", policy_v12, version="policy-v12")
                step.ensure_fresh(snapshot, current_version="policy-v14")
        except Exception as exc:
            return _caught(run, str(exc))
        return _missed(run, "stale policy was not blocked")

    return BenchmarkCase(
        name="stale_policy_snapshot",
        category="state_freshness",
        description="approval uses an old policy snapshot",
        raw=raw,
        protected=protected,
    )


def dropped_handoff_fact() -> BenchmarkCase:
    def raw() -> ScenarioResult:
        return ScenarioResult(
            reported_success=True,
            business_success=False,
            caught_false_success=False,
            reason="downstream agent acted without previous_refund_count",
        )

    def protected() -> ScenarioResult:
        run = WorkflowRun("bench-dropped-handoff")
        try:
            with run.step("intake-agent", "handoff_refund", step_id="handoff") as step:
                step.handoff(
                    to_agent="refund-agent",
                    task="issue refund",
                    facts={"order_id": "ord_1", "amount": 42.5},
                    required_facts=["order_id", "amount", "previous_refund_count"],
                )
        except Exception as exc:
            return _caught(run, str(exc))
        return _missed(run, "missing handoff fact was not blocked")

    return BenchmarkCase(
        name="dropped_handoff_fact",
        category="handoff_contract",
        description="required handoff fact is missing",
        raw=raw,
        protected=protected,
    )


def partial_write_claim() -> BenchmarkCase:
    visible_write = {"profile_updated": True, "audit_written": False}

    def raw() -> ScenarioResult:
        return ScenarioResult(
            reported_success=True,
            business_success=False,
            caught_false_success=False,
            reason="agent claimed update complete after only the profile write",
        )

    def protected() -> ScenarioResult:
        run = WorkflowRun("bench-partial-write")
        try:
            with run.step("account-agent", "update_account", step_id="account") as step:
                step.write_state("profile", {"updated": True}, version="profile-v2")
                step.verify_outcome(
                    "audit_recorded",
                    lambda: visible_write["audit_written"],
                    failure_reason="audit record was not visible",
                    details=visible_write,
                )
        except Exception as exc:
            return _caught(run, str(exc))
        return _missed(run, "partial write was not blocked")

    return BenchmarkCase(
        name="partial_write_claim",
        category="outcome_verification",
        description="agent claims a multi-write operation completed after a partial write",
        raw=raw,
        protected=protected,
    )


def wrong_entity_action() -> BenchmarkCase:
    provider_result = {"requested_order_id": "ord_1", "refunded_order_id": "ord_2"}

    def raw() -> ScenarioResult:
        return ScenarioResult(
            reported_success=True,
            business_success=False,
            caught_false_success=False,
            reason="agent refunded ord_2 while telling ord_1 customer it was done",
        )

    def protected() -> ScenarioResult:
        run = WorkflowRun("bench-wrong-entity")
        try:
            with run.step(
                "refund-agent",
                "issue_refund",
                step_id="refund",
                criticality="financial",
            ) as step:
                step.verify_outcome(
                    "correct_entity_refunded",
                    lambda: (
                        provider_result["refunded_order_id"]
                        == provider_result["requested_order_id"]
                    ),
                    failure_reason="refund provider confirmed a different order",
                    details=provider_result,
                    criticality="financial",
                )
        except Exception as exc:
            return _caught(run, str(exc))
        return _missed(run, "wrong entity action was not blocked")

    return BenchmarkCase(
        name="wrong_entity_action",
        category="outcome_verification",
        description="tool acts on the wrong entity while the agent reports success",
        raw=raw,
        protected=protected,
    )


def swallowed_tool_error() -> BenchmarkCase:
    def raw() -> ScenarioResult:
        try:
            raise RuntimeError("email provider unavailable")
        except RuntimeError:
            return ScenarioResult(
                reported_success=True,
                business_success=False,
                caught_false_success=False,
                reason="agent swallowed provider error and reported message sent",
            )

    def protected() -> ScenarioResult:
        run = WorkflowRun("bench-swallowed-error")
        try:
            with run.step("message-agent", "send_customer_email", step_id="email") as step:
                step.verify_outcome(
                    "customer_email_sent",
                    lambda: False,
                    failure_reason="email provider did not accept the message",
                    details={"provider_error": "email provider unavailable"},
                )
        except Exception as exc:
            return _caught(run, str(exc))
        return _missed(run, "swallowed tool error was not blocked")

    return BenchmarkCase(
        name="swallowed_tool_error",
        category="outcome_verification",
        description="agent reports success after swallowing a tool error",
        raw=raw,
        protected=protected,
    )


def default_cases() -> list[BenchmarkCase]:
    return [
        pending_refund_not_settled(),
        stale_policy_snapshot(),
        dropped_handoff_fact(),
        partial_write_claim(),
        wrong_entity_action(),
        swallowed_tool_error(),
    ]


def run_cases(cases: Optional[Sequence[BenchmarkCase]] = None) -> list[BenchmarkCaseResult]:
    selected = list(cases or default_cases())
    return [
        BenchmarkCaseResult(case=case, raw=case.raw(), protected=case.protected())
        for case in selected
    ]


def categories(results: Iterable[BenchmarkCaseResult]) -> list[str]:
    return sorted({result.case.category for result in results})


def _caught(run: WorkflowRun, reason: str) -> ScenarioResult:
    return ScenarioResult(
        reported_success=False,
        business_success=False,
        caught_false_success=True,
        reason=reason,
        receipt_statuses=tuple(receipt.status for receipt in run.receipts()),
    )


def _missed(run: WorkflowRun, reason: str) -> ScenarioResult:
    return ScenarioResult(
        reported_success=True,
        business_success=False,
        caught_false_success=False,
        reason=reason,
        receipt_statuses=tuple(receipt.status for receipt in run.receipts()),
    )
