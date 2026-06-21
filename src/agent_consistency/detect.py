from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .reporting import load_receipt_report

SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}
CUSTOMER_VISIBLE_TERMS = (
    "customer",
    "email",
    "message",
    "notify",
    "reply",
    "sms",
    "comms",
)
SIDE_EFFECT_TERMS = (
    "approve",
    "cancel",
    "charge",
    "close",
    "create",
    "delete",
    "email",
    "issue",
    "message",
    "notify",
    "refund",
    "send",
    "ship",
    "update",
    "write",
)


@dataclass(frozen=True)
class RiskFinding:
    finding_type: str
    severity: str
    explanation: str
    step_id: str
    agent: str
    action: str
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.finding_type,
            "finding_type": self.finding_type,
            "severity": self.severity,
            "explanation": self.explanation,
            "step_id": self.step_id,
            "agent": self.agent,
            "action": self.action,
            "details": self.details,
        }


@dataclass(frozen=True)
class RiskReport:
    run_id: str
    source: Optional[str]
    receipt_count: int
    findings: List[RiskFinding]

    @property
    def has_high_severity(self) -> bool:
        return any(finding.severity == "high" for finding in self.findings)

    @property
    def ranked_findings(self) -> List[RiskFinding]:
        return sorted(
            self.findings,
            key=lambda finding: (
                SEVERITY_ORDER.get(finding.severity, 99),
                finding.step_id,
                finding.finding_type,
            ),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "source": self.source,
            "receipt_count": self.receipt_count,
            "findings": [finding.to_dict() for finding in self.ranked_findings],
            "has_high_severity": self.has_high_severity,
        }


def detect_receipt_file(path: str) -> RiskReport:
    report = load_receipt_report(path)
    return detect_risks(report, source=str(report.get("source") or path))


def detect_risks(receipts_or_report: Any, *, source: Optional[str] = None) -> RiskReport:
    if isinstance(receipts_or_report, Mapping) and "receipts" in receipts_or_report:
        report = receipts_or_report
        receipts = [_receipt_payload(item) for item in report.get("receipts") or []]
        run_id = str(report.get("run_id") or _infer_run_id(receipts))
        report_source = source or _optional_str(report.get("source"))
    else:
        receipts = [_receipt_payload(item) for item in receipts_or_report]
        run_id = _infer_run_id(receipts)
        report_source = source

    findings: List[RiskFinding] = []
    unresolved_reasons: List[str] = []
    for receipt in receipts:
        context = _ReceiptContext(receipt)
        if context.is_customer_visible and unresolved_reasons:
            findings.append(
                context.finding(
                    "customer_action_after_unverified_outcome",
                    "high",
                    (
                        "Customer-visible action ran while an earlier outcome or gate was "
                        "unresolved: "
                        + "; ".join(unresolved_reasons)
                    ),
                    {"unresolved": list(unresolved_reasons)},
                )
            )

        missing_gate = _missing_outcome_gate(context)
        if missing_gate:
            findings.append(missing_gate)
            if not context.is_customer_visible:
                unresolved_reasons.append(
                    f"{context.step_id} performed {context.action} without an outcome gate"
                )

        for outcome in context.outcomes:
            if bool(outcome.get("passed")):
                continue
            outcome_name = str(outcome.get("name") or "outcome")
            reason = str(outcome.get("reason") or "postcondition failed")
            findings.append(
                context.finding(
                    "failed_outcome",
                    "high",
                    f"Outcome '{outcome_name}' failed before continuation: {reason}",
                    {"outcome": outcome},
                )
            )
            unresolved_reasons.append(f"{context.step_id} failed outcome '{outcome_name}'")

        for issue in context.issues:
            issue_finding = _issue_finding(context, issue)
            if issue_finding:
                findings.append(issue_finding)
                if issue_finding.finding_type in {
                    "stale_state_read",
                    "dropped_handoff_fact",
                    "handoff_contract_failed",
                    "unsupported_customer_claim",
                }:
                    unresolved_reasons.append(
                        f"{context.step_id} reported {issue_finding.finding_type}"
                    )

    return RiskReport(
        run_id=run_id,
        source=report_source,
        receipt_count=len(receipts),
        findings=findings,
    )


def render_risk_report(report: RiskReport) -> str:
    lines = [
        f"Run: {report.run_id}",
        f"Receipts: {report.receipt_count}",
    ]
    if report.source:
        lines.append(f"Source: {report.source}")
    lines.append("")
    if not report.findings:
        lines.append("Risk status: CLEAN")
        lines.append("No false-success risks were detected from the declared receipts.")
        return "\n".join(lines) + "\n"

    status = "HIGH RISK" if report.has_high_severity else "NEEDS REVIEW"
    lines.append(f"Risk status: {status}")
    lines.append("")
    lines.append("Findings:")
    for finding in report.ranked_findings:
        lines.append(
            f"- {finding.severity.upper()} {finding.finding_type} "
            f"at {finding.step_id}: {finding.explanation}"
        )
    lines.append("")
    lines.append(
        "Detect mode reports missing gates, stale reads, dropped handoff facts, "
        "failed outcomes, and customer-visible actions after unresolved or unverified outcomes."
    )
    lines.append(
        "It cannot know what an agent claimed unless the workflow declares the outcomes "
        "and evidence that matter."
    )
    return "\n".join(lines) + "\n"


class _ReceiptContext:
    def __init__(self, receipt: Mapping[str, Any]) -> None:
        self.receipt = receipt
        self.step_id = str(receipt.get("step_id") or "unknown-step")
        self.agent = str(receipt.get("agent") or "unknown-agent")
        self.action = str(receipt.get("action") or "unknown-action")
        self.outcomes = list(receipt.get("outcomes") or [])
        self.issues = list(receipt.get("issues") or [])

    @property
    def is_customer_visible(self) -> bool:
        return _has_any_term([self.agent, self.action], CUSTOMER_VISIBLE_TERMS)

    @property
    def is_side_effect(self) -> bool:
        return _has_any_term([self.action], SIDE_EFFECT_TERMS)

    def finding(
        self,
        finding_type: str,
        severity: str,
        explanation: str,
        details: Optional[Mapping[str, Any]] = None,
    ) -> RiskFinding:
        return RiskFinding(
            finding_type=finding_type,
            severity=severity,
            explanation=explanation,
            step_id=self.step_id,
            agent=self.agent,
            action=self.action,
            details=dict(details or {}),
        )


def _missing_outcome_gate(context: _ReceiptContext) -> Optional[RiskFinding]:
    if context.outcomes or not context.is_side_effect:
        return None
    severity = "high" if context.is_customer_visible else "medium"
    return context.finding(
        "missing_gate",
        severity,
        (
            f"Side-effect action '{context.action}' recorded no outcome gate. "
            "The receipt cannot show whether the real-world result became true."
        ),
    )


def _issue_finding(
    context: _ReceiptContext,
    issue: Mapping[str, Any],
) -> Optional[RiskFinding]:
    code = str(issue.get("code") or "")
    message = str(issue.get("message") or "")
    details = {"issue": dict(issue)}
    if code == "stale_state":
        return context.finding(
            "stale_state_read",
            "high",
            f"The step used stale state before acting: {message}",
            details,
        )
    if code in {"invalid_handoff", "invalid_consumed_handoff"}:
        finding_type = "dropped_handoff_fact" if "required fact" in message else (
            "handoff_contract_failed"
        )
        return context.finding(
            finding_type,
            "high",
            f"The handoff contract was not satisfied: {message}",
            details,
        )
    if code == "unsupported_claim":
        return context.finding(
            "unsupported_customer_claim",
            "high" if context.is_customer_visible else "medium",
            f"A claim was made without the required supporting facts or evidence: {message}",
            details,
        )
    return None


def _receipt_payload(item: Any) -> Dict[str, Any]:
    if hasattr(item, "to_dict"):
        return item.to_dict()
    return dict(item)


def _infer_run_id(receipts: Iterable[Mapping[str, Any]]) -> str:
    for receipt in receipts:
        if receipt.get("run_id"):
            return str(receipt["run_id"])
    return "unknown-run"


def _has_any_term(values: Iterable[str], terms: Iterable[str]) -> bool:
    haystack = " ".join(str(value).lower() for value in values)
    return any(term in haystack for term in terms)


def _optional_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    return str(value)
