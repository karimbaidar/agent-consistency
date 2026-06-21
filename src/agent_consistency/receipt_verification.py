import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from .models import RECEIPT_DIGEST_FIELD, compute_receipt_digest


@dataclass(frozen=True)
class VerificationIssue:
    area: str
    message: str
    line: Optional[int] = None
    receipt: str = ""

    def render(self) -> str:
        location = ""
        if self.receipt:
            location = f" at {self.receipt}"
        elif self.line is not None:
            location = f" at line {self.line}"
        return f"- [{self.area}]{location}: {self.message}"


@dataclass(frozen=True)
class ReceiptVerificationReport:
    path: str
    receipt_count: int
    chain_present: bool
    structural_errors: List[VerificationIssue] = field(default_factory=list)
    integrity_errors: List[VerificationIssue] = field(default_factory=list)
    semantic_errors: List[VerificationIssue] = field(default_factory=list)
    semantic_findings: List[VerificationIssue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not (self.structural_errors or self.integrity_errors or self.semantic_errors)

    @property
    def run_status(self) -> str:
        if self.semantic_errors:
            return "inconsistent"
        blocked = [
            finding
            for finding in self.semantic_findings
            if finding.message.startswith("blocked gate")
        ]
        if blocked:
            return f"failed as expected - {len(blocked)} blocked receipt(s)"
        return "passed"

    @property
    def integrity_status(self) -> str:
        if self.integrity_errors:
            return "failed"
        if self.chain_present:
            return "verified"
        return "not present"


def verify_receipt_file(path: str) -> ReceiptVerificationReport:
    source = Path(path)
    structural_errors: List[VerificationIssue] = []
    integrity_errors: List[VerificationIssue] = []
    semantic_errors: List[VerificationIssue] = []
    semantic_findings: List[VerificationIssue] = []

    payloads = _load_jsonl_payloads(source, structural_errors)
    chain_present = any(bool(payload.get(RECEIPT_DIGEST_FIELD)) for payload in payloads)

    for index, payload in enumerate(payloads, start=1):
        _validate_required_fields(payload, index, structural_errors, chain_present)

    if chain_present:
        _validate_digest_chain(payloads, integrity_errors)

    _validate_references(payloads, structural_errors)
    _interpret_semantics(payloads, semantic_errors, semantic_findings)

    return ReceiptVerificationReport(
        path=str(source),
        receipt_count=len(payloads),
        chain_present=chain_present,
        structural_errors=structural_errors,
        integrity_errors=integrity_errors,
        semantic_errors=semantic_errors,
        semantic_findings=semantic_findings,
    )


def render_verify_report(report: ReceiptVerificationReport) -> str:
    lines = [
        f"Receipt verification: {report.path}",
        f"Receipts: {report.receipt_count}",
        f"Integrity: {report.integrity_status}",
        f"Run status: {report.run_status}",
        f"Structural checks: {'passed' if not report.structural_errors else 'failed'}",
    ]
    if report.integrity_status == "not present":
        lines.append("Digest chain: not present on these receipts")
    elif report.integrity_status == "verified":
        lines.append("Digest chain: verified")
    lines.append("")

    errors = report.structural_errors + report.integrity_errors + report.semantic_errors
    if errors:
        lines.append("Errors:")
        lines.extend(issue.render() for issue in errors)
        lines.append("")

    if report.semantic_findings:
        lines.append("Semantic interpretation:")
        lines.extend(issue.render() for issue in report.semantic_findings)
        lines.append("")

    lines.append("Result: OK" if report.ok else "Result: FAILED")
    return "\n".join(lines) + "\n"


def _load_jsonl_payloads(path: Path, errors: List[VerificationIssue]) -> List[Dict[str, Any]]:
    if not path.exists():
        errors.append(VerificationIssue("structural", f"file does not exist: {path}"))
        return []
    payloads: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append(
                    VerificationIssue(
                        "structural",
                        f"invalid JSON: {exc.msg}",
                        line=line_number,
                    )
                )
                continue
            if not isinstance(payload, dict):
                errors.append(
                    VerificationIssue(
                        "structural",
                        "receipt line is not a JSON object",
                        line_number,
                    )
                )
                continue
            payloads.append(payload)
    if not payloads and not errors:
        errors.append(VerificationIssue("structural", "no receipts found"))
    return payloads


def _validate_required_fields(
    payload: Mapping[str, Any],
    line_number: int,
    errors: List[VerificationIssue],
    chain_present: bool,
) -> None:
    for field_name in ("run_id", "step_id", "agent", "action", "status", "created_at"):
        if _is_blank(payload.get(field_name)):
            errors.append(
                VerificationIssue(
                    "structural",
                    f"missing required field '{field_name}'",
                    line=line_number,
                    receipt=_receipt_label(payload),
                )
            )
    if str(payload.get("status") or "") != "running" and _is_blank(payload.get("finished_at")):
        errors.append(
            VerificationIssue(
                "structural",
                "missing required field 'finished_at'",
                line=line_number,
                receipt=_receipt_label(payload),
            )
        )
    for list_field in (
        "state_reads",
        "state_deltas",
        "handoffs",
        "proof_artifacts",
        "outcomes",
        "issues",
        "parent_receipt_keys",
        "consumed_handoff_ids",
        "produced_handoff_ids",
        "consumed_artifact_ids",
    ):
        if list_field in payload and not isinstance(payload[list_field], list):
            errors.append(
                VerificationIssue(
                    "structural",
                    f"field '{list_field}' must be a list",
                    line=line_number,
                    receipt=_receipt_label(payload),
                )
            )
    if chain_present:
        for field_name in ("schema_version", "receipt_id", RECEIPT_DIGEST_FIELD):
            if _is_blank(payload.get(field_name)):
                errors.append(
                    VerificationIssue(
                        "structural",
                        f"missing required chain field '{field_name}'",
                        line=line_number,
                        receipt=_receipt_label(payload),
                    )
                )


def _validate_digest_chain(
    payloads: Sequence[Mapping[str, Any]],
    errors: List[VerificationIssue],
) -> None:
    previous_digest: Optional[str] = None
    for payload in payloads:
        label = _receipt_label(payload)
        stored_digest = payload.get(RECEIPT_DIGEST_FIELD)
        if not stored_digest:
            errors.append(
                VerificationIssue("integrity", "receipt digest is missing", receipt=label)
            )
            continue
        computed_digest = compute_receipt_digest(payload)
        if stored_digest != computed_digest:
            errors.append(
                VerificationIssue(
                    "integrity",
                    (
                        "digest mismatch "
                        f"(stored {str(stored_digest)[:12]}, computed {computed_digest[:12]})"
                    ),
                    receipt=label,
                )
            )
        actual_previous = payload.get("previous_receipt_digest")
        if actual_previous != previous_digest:
            expected = previous_digest[:12] if previous_digest else "None"
            actual = str(actual_previous)[:12] if actual_previous else "None"
            errors.append(
                VerificationIssue(
                    "integrity",
                    f"previous digest mismatch (expected {expected}, got {actual})",
                    receipt=label,
                )
            )
        previous_digest = str(stored_digest)


def _validate_references(
    payloads: Sequence[Mapping[str, Any]],
    errors: List[VerificationIssue],
) -> None:
    prior_receipt_keys = set()
    prior_handoff_ids = set()
    prior_artifact_ids = set()

    for payload in payloads:
        label = _receipt_label(payload)
        for parent in _as_list(payload.get("parent_receipt_keys")):
            if parent not in prior_receipt_keys:
                errors.append(
                    VerificationIssue(
                        "structural",
                        f"parent receipt reference does not resolve: {parent}",
                        receipt=label,
                    )
                )
        for handoff_id in _as_list(payload.get("consumed_handoff_ids")):
            if handoff_id not in prior_handoff_ids:
                errors.append(
                    VerificationIssue(
                        "structural",
                        f"consumed handoff reference does not resolve: {handoff_id}",
                        receipt=label,
                    )
                )
        for artifact_id in _as_list(payload.get("consumed_artifact_ids")):
            if artifact_id not in prior_artifact_ids:
                errors.append(
                    VerificationIssue(
                        "structural",
                        f"consumed artifact reference does not resolve: {artifact_id}",
                        receipt=label,
                    )
                )

        prior_receipt_keys.add(_receipt_key(payload))
        for handoff in _as_list(payload.get("handoffs")):
            if isinstance(handoff, Mapping) and handoff.get("handoff_id"):
                prior_handoff_ids.add(str(handoff["handoff_id"]))
        for artifact in _as_list(payload.get("proof_artifacts")):
            if isinstance(artifact, Mapping) and artifact.get("artifact_id"):
                prior_artifact_ids.add(str(artifact["artifact_id"]))


def _interpret_semantics(
    payloads: Sequence[Mapping[str, Any]],
    errors: List[VerificationIssue],
    findings: List[VerificationIssue],
) -> None:
    for payload in payloads:
        label = _receipt_label(payload)
        failed_outcomes = [
            outcome
            for outcome in _as_list(payload.get("outcomes"))
            if isinstance(outcome, Mapping) and outcome.get("passed") is False
        ]
        error_issues = [
            issue
            for issue in _as_list(payload.get("issues"))
            if isinstance(issue, Mapping) and str(issue.get("severity") or "error") == "error"
        ]
        status = str(payload.get("status") or "")

        if (failed_outcomes or error_issues or payload.get("error")) and status != "failed":
            errors.append(
                VerificationIssue(
                    "semantic",
                    "receipt has failed outcomes or errors but status is not failed",
                    receipt=label,
                )
            )

        if status == "failed":
            detail = _failure_detail(payload, failed_outcomes, error_issues)
            findings.append(
                VerificationIssue("semantic", f"blocked gate - {detail}", receipt=label)
            )
        for outcome in failed_outcomes:
            reason = str(outcome.get("reason") or "outcome failed")
            findings.append(
                VerificationIssue(
                    "semantic",
                    f"outcome {outcome.get('name', 'outcome')} failed - {reason}",
                    receipt=label,
                )
            )


def _failure_detail(
    payload: Mapping[str, Any],
    failed_outcomes: List[Mapping[str, Any]],
    error_issues: List[Mapping[str, Any]],
) -> str:
    if failed_outcomes:
        outcome = failed_outcomes[0]
        return f"{outcome.get('name', 'outcome')} failed"
    if error_issues:
        issue = error_issues[0]
        return f"{issue.get('code', 'issue')}: {issue.get('message', '')}"
    error = payload.get("error")
    if isinstance(error, Mapping):
        return f"{error.get('type', 'error')}: {error.get('message', '')}"
    return "receipt status is failed"


def _receipt_label(payload: Mapping[str, Any]) -> str:
    return str(payload.get("receipt_id") or _receipt_key(payload) or "unknown receipt")


def _receipt_key(payload: Mapping[str, Any]) -> str:
    run_id = payload.get("run_id")
    step_id = payload.get("step_id")
    if run_id and step_id:
        return f"{run_id}:{step_id}"
    return ""


def _as_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _is_blank(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}
