import ast
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}
CONFIDENCE_ORDER = {"high": 0, "medium": 1, "low": 2}
SOURCE_EXTENSIONS = {".py", ".js", ".jsx", ".ts", ".tsx"}
TEST_FILE_MARKERS = (".test.", ".spec.", "_test.")
DEV_FILE_MARKERS = ("dev_", ".story.", ".stories.")
DEFAULT_EXCLUDED_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "benchmark",
    "build",
    "dist",
    "docs",
    "examples",
    "node_modules",
    "site",
    "tests",
    "venv",
}
SUPPRESSION_MARKER = "agent-consistency: ignore false-success-risk"

RISKY_ACTIONS = (
    "send_email",
    "send_message",
    "notify_customer",
    "refund",
    "issue_refund",
    "delete_user",
    "remove_account",
    "close_ticket",
    "resolve_ticket",
    "grant_access",
    "assign_role",
    "submit_order",
    "place_trade",
    "cancel_order",
    "approve",
    "provision",
    "deploy",
    "update_record",
    "write_state",
    "mark_complete",
)
GENERIC_HELPER_ACTIONS = {
    "send_email",
    "send_message",
    "notify_customer",
    "update_record",
    "write_state",
}
DANGEROUS_MESSAGE_TERMS = (
    "complete",
    "completed",
    "done",
    "resolved",
    "deleted",
    "refunded",
    "approved",
    "access granted",
    "order filled",
    "ticket closed",
)
PROTECTION_TERMS = (
    "verified_action",
    "reliability_gate",
    "verify_outcome",
    "outcomeverifier",
    "refund_settled",
    "read_after_write",
    "verified_step",
    "verified_tool",
    "verified_node",
)
OUTCOME_TERMS = (
    'status == "settled"',
    "status == 'settled'",
    'status == "delivered"',
    "status == 'delivered'",
    'status == "resolved"',
    "status == 'resolved'",
    'status == "deleted"',
    "status == 'deleted'",
    'status == "active"',
    "status == 'active'",
    'status == "filled"',
    "status == 'filled'",
    "refund_settled",
)
IDEMPOTENCY_TERMS = ("idempotency_key", "idempotent", "dedupe_key")
AGENTIC_TERMS = (
    "agent",
    "agents",
    "workflow",
    "workflows",
    "handoff",
    "handoffs",
    "tool_call",
    "tool_calls",
    "tool_result",
    "orchestrator",
    "planner",
    "executor",
    "llm",
    "prompt",
    "assistant",
    "model_provider",
)
FRAMEWORK_TERMS = {
    "LangGraph": ("langgraph", "stategraph"),
    "CrewAI": ("crewai", "crew"),
    "AutoGen": ("autogen", "autogen_core"),
    "Semantic Kernel": ("semantic_kernel", "semantickernel"),
    "Microsoft Agent Framework": ("agent_framework", "workflowcontext"),
    "OpenAI Agents": ("openai_agents", "agents.run", "runcontextwrapper"),
    "LlamaIndex": ("llama_index", "llamaindex"),
}
INTERNAL_MESSAGE_TERMS = (
    "ctx.send_message",
    "workflowcontext",
    "agentworkflow",
    "courtworkflowstate",
    "message_envelope",
    "messagecontext",
    "messagedroppedexception",
    "_process_send",
    "_send_message",
    "runtime_message",
    "telemetry_metadata",
    "elicitation",
    "websocket",
    "wsbridge",
    "singlethreadedagentruntime",
    "_worker_runtime",
    "routedagent",
)
CUSTOMER_TERMS = ("customer", "client", "user_email", "email", "ticket", "refund", "account")


class ScanError(RuntimeError):
    pass


@dataclass(frozen=True)
class ScanProfile:
    applicability: str = "general-code"
    confidence: str = "low"
    summary: str = "No clear agent workflow surface was detected."
    agentic_files: int = 0
    action_files: int = 0
    framework_signals: List[str] = field(default_factory=list)
    signal_terms: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "applicability": self.applicability,
            "confidence": self.confidence,
            "summary": self.summary,
            "agentic_files": self.agentic_files,
            "action_files": self.action_files,
            "framework_signals": list(self.framework_signals),
            "signal_terms": list(self.signal_terms),
        }


@dataclass(frozen=True)
class ScanFinding:
    severity: str
    confidence: str
    path: str
    line: int
    action: str
    why: str
    evidence_found: List[str] = field(default_factory=list)
    evidence_missing: List[str] = field(default_factory=list)
    suggested_fix: str = ""
    snippet: str = ""
    category: str = "general"
    rule: str = "risky_action_without_confirmation"
    fingerprint: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "severity": self.severity,
            "confidence": self.confidence,
            "path": self.path,
            "line": self.line,
            "action": self.action,
            "why": self.why,
            "evidence_found": list(self.evidence_found),
            "evidence_missing": list(self.evidence_missing),
            "suggested_fix": self.suggested_fix,
            "snippet": self.snippet,
            "category": self.category,
            "rule": self.rule,
            "fingerprint": self.fingerprint,
        }


@dataclass(frozen=True)
class ScanReport:
    repository: str
    source: str
    findings: List[ScanFinding]
    verified_actions_found: int = 0
    files_scanned: int = 0
    baseline_path: Optional[str] = None
    suppressed_by_baseline: int = 0
    profile: ScanProfile = field(default_factory=ScanProfile)

    @property
    def risky_actions_found(self) -> int:
        return len(self.finding_groups)

    @property
    def high_severity(self) -> int:
        return self._count("high")

    @property
    def medium_severity(self) -> int:
        return self._count("medium")

    @property
    def low_severity(self) -> int:
        return self._count("low")

    @property
    def false_success_exposure(self) -> int:
        return len(self.findings)

    @property
    def idempotency_gaps(self) -> int:
        return sum(
            1
            for finding in self.findings
            if any("idempotency" in item for item in finding.evidence_missing)
        )

    @property
    def missing_outcome_checks(self) -> int:
        return sum(
            1
            for finding in self.findings
            if any("outcome" in item or "confirmation" in item for item in finding.evidence_missing)
        )

    @property
    def missing_handoff_facts(self) -> int:
        return sum(1 for finding in self.findings if "handoff" in finding.rule)

    @property
    def risk_score(self) -> int:
        score = (
            self.high_severity * 24
            + self.medium_severity * 12
            + self.low_severity * 4
            + min(self.false_success_exposure, 18)
        )
        return min(100, score)

    @property
    def confidence(self) -> str:
        if any(finding.confidence == "high" for finding in self.findings):
            return "medium"
        if self.findings:
            return "low"
        if self.profile.applicability == "general-code":
            return "low"
        return "high"

    @property
    def finding_groups(self) -> List[Dict[str, Any]]:
        return _finding_groups(self.ranked_findings)

    @property
    def ranked_findings(self) -> List[ScanFinding]:
        return sorted(
            self.findings,
            key=lambda finding: (
                SEVERITY_ORDER.get(finding.severity, 99),
                finding.path,
                finding.line,
                finding.action,
            ),
        )

    def has_severity_at_or_above(self, threshold: str) -> bool:
        threshold_rank = SEVERITY_ORDER[threshold]
        return any(SEVERITY_ORDER[finding.severity] <= threshold_rank for finding in self.findings)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "repository": self.repository,
            "source": self.source,
            "files_scanned": self.files_scanned,
            "applicability": self.profile.applicability,
            "applicability_confidence": self.profile.confidence,
            "applicability_summary": self.profile.summary,
            "agentic_files": self.profile.agentic_files,
            "action_files": self.profile.action_files,
            "framework_signals": list(self.profile.framework_signals),
            "signal_terms": list(self.profile.signal_terms),
            "risk_score": self.risk_score,
            "confidence": self.confidence,
            "risky_actions_found": self.risky_actions_found,
            "high_severity": self.high_severity,
            "medium_severity": self.medium_severity,
            "low_severity": self.low_severity,
            "false_success_exposure": self.false_success_exposure,
            "verified_actions_found": self.verified_actions_found,
            "idempotency_gaps": self.idempotency_gaps,
            "missing_outcome_checks": self.missing_outcome_checks,
            "missing_handoff_facts": self.missing_handoff_facts,
            "baseline_path": self.baseline_path,
            "suppressed_by_baseline": self.suppressed_by_baseline,
            "finding_groups": [_finding_group_to_dict(group) for group in self.finding_groups],
            "findings": [finding.to_dict() for finding in self.ranked_findings],
        }

    def _count(self, severity: str) -> int:
        return sum(1 for group in self.finding_groups if group["severity"] == severity)


def scan_target(
    target: str,
    *,
    baseline_path: Optional[str] = None,
) -> ScanReport:
    baseline = load_baseline(baseline_path) if baseline_path else set()
    if _is_github_url(target):
        return _scan_github_url(target, baseline=baseline, baseline_path=baseline_path)
    return scan_path(Path(target), baseline=baseline, baseline_path=baseline_path)


def scan_path(
    path: Path,
    *,
    baseline: Optional[set[str]] = None,
    baseline_path: Optional[str] = None,
    repository: Optional[str] = None,
    source: Optional[str] = None,
) -> ScanReport:
    if not path.exists():
        raise ScanError(f"scan target does not exist: {path}")

    root = path if path.is_dir() else path.parent
    files = [path] if path.is_file() else list(_iter_source_files(path))
    profile = _profile_repo(files, root)
    findings: List[ScanFinding] = []
    verified_actions_found = 0
    for file_path in files:
        file_findings, verified = _scan_file(file_path, root)
        findings.extend(file_findings)
        verified_actions_found += verified

    baseline = baseline or set()
    filtered = [finding for finding in findings if finding.fingerprint not in baseline]
    return ScanReport(
        repository=repository or _repository_name(path),
        source=source or str(path),
        findings=_dedupe_findings(filtered),
        verified_actions_found=verified_actions_found,
        files_scanned=len(files),
        baseline_path=baseline_path,
        suppressed_by_baseline=len(findings) - len(filtered),
        profile=profile,
    )


def _profile_repo(files: List[Path], root: Path) -> ScanProfile:
    framework_signals: set[str] = set()
    signal_terms: set[str] = set()
    agentic_files = 0
    action_files = 0

    for path in files:
        try:
            sample = path.read_text(encoding="utf-8", errors="ignore")[:40_000]
        except OSError:
            continue
        haystack = _normalize(f"{_relative_path(path, root)}\n{sample}")
        file_is_agentic = False

        for label, terms in FRAMEWORK_TERMS.items():
            if any(_normalize(term) in haystack for term in terms):
                framework_signals.add(label)
                file_is_agentic = True
        for term in AGENTIC_TERMS:
            normalized_term = _normalize(term).strip("_")
            if _token_or_phrase_present(haystack, normalized_term):
                signal_terms.add(normalized_term)
                file_is_agentic = True
        if any(_normalize(action).strip("_") in haystack for action in RISKY_ACTIONS):
            action_files += 1
        if file_is_agentic:
            agentic_files += 1

    if framework_signals or agentic_files >= 3:
        applicability = "agentic-workflow"
        confidence = "high" if framework_signals or agentic_files >= 8 else "medium"
        summary = "This repo looks like an AI agent or workflow codebase."
    elif agentic_files or action_files:
        applicability = "workflow-adjacent"
        confidence = "medium" if action_files else "low"
        summary = "This repo has workflow or side-effect signals, but weak agentic evidence."
    else:
        applicability = "general-code"
        confidence = "low"
        summary = "This repo does not look agentic; scan results are a broad safety pass only."

    return ScanProfile(
        applicability=applicability,
        confidence=confidence,
        summary=summary,
        agentic_files=agentic_files,
        action_files=action_files,
        framework_signals=sorted(framework_signals),
        signal_terms=sorted(signal_terms)[:12],
    )


def render_scan_text(report: ScanReport) -> str:
    lines = [
        "False-success report card",
        "",
        f"Repository: {report.repository}",
        f"Repo fit: {report.profile.applicability} ({report.profile.confidence})",
        f"Risky actions found: {report.risky_actions_found}",
        f"High severity: {report.high_severity}",
        f"False-success exposure: {report.false_success_exposure} unguarded actions",
        f"Confidence: {report.confidence}",
    ]
    if report.suppressed_by_baseline:
        lines.append(f"Suppressed by baseline: {report.suppressed_by_baseline}")
    lines.append("")
    if not report.findings:
        lines.append("No false-success risks were detected by the static scanner.")
        lines.append("This does not prove the repo is safe; it means no configured pattern fired.")
        return "\n".join(lines) + "\n"

    top_group = report.finding_groups[0]
    top = top_group["representative"]
    lines.extend(
        [
            "Top finding:",
            f"{top_group['action']} {top_group['why']}",
            f"Representative file: {top.path}:{top.line}",
            f"Severity/confidence: {top_group['severity'].upper()} / {top_group['confidence']}",
            f"Occurrences: {top_group['count']}",
            "",
            "Findings:",
        ]
    )
    for group in report.finding_groups:
        if group["confidence"] == "low":
            lines.append("Possible risk, needs review.")
        lines.append(
            f"{group['severity'].upper()}  {group['action']} "
            f"({group['confidence']} confidence, {group['count']} occurrence(s))"
        )
        lines.append(f"      {group['why']}")
    return "\n".join(lines) + "\n"


def render_scan_markdown(report: ScanReport) -> str:
    lines = [
        "# False-success report card",
        "",
        f"Repository: `{report.repository}`",
        f"Repo fit: `{report.profile.applicability}` ({report.profile.confidence})",
        f"Repo fit note: {report.profile.summary}",
        f"Risk score: {report.risk_score} / 100 (heuristic)",
        f"Confidence: {report.confidence}",
        f"False-success exposure: {report.false_success_exposure} unguarded actions",
        "",
        "## Summary",
        "",
        f"* Risky actions found: {report.risky_actions_found}",
        f"* High severity: {report.high_severity}",
        f"* Medium severity: {report.medium_severity}",
        f"* Low severity: {report.low_severity}",
        f"* Raw exposure: {report.false_success_exposure}",
        f"* Files scanned: {report.files_scanned}",
        f"* Agentic files: {report.profile.agentic_files}",
        f"* Verified actions found: {report.verified_actions_found}",
        f"* Idempotency gaps: {report.idempotency_gaps}",
        f"* Missing outcome checks: {report.missing_outcome_checks}",
        f"* Missing handoff facts: {report.missing_handoff_facts}",
    ]
    if report.suppressed_by_baseline:
        lines.append(f"* Suppressed by baseline: {report.suppressed_by_baseline}")
    if not report.findings:
        lines.extend(
            [
                "",
                "No configured false-success scanner finding fired.",
                "",
                "_This is a static scan, not a proof of safety._",
            ]
        )
        return "\n".join(lines) + "\n"

    grouped = (
        ("High-risk findings", "high"),
        ("Medium-risk findings", "medium"),
        ("Low-risk findings", "low"),
    )
    for title, severity in grouped:
        severity_groups = [
            group for group in report.finding_groups if group["severity"] == severity
        ]
        if not severity_groups:
            continue
        lines.extend(["", f"## {title}", ""])
        for group in severity_groups:
            lines.extend(_finding_group_markdown(group))
    return "\n".join(lines) + "\n"


def write_baseline(report: ScanReport, path: str = "agent-consistency-baseline.json") -> None:
    payload = {
        "schema_version": 1,
        "repository": report.repository,
        "findings": [
            {
                "fingerprint": finding.fingerprint,
                "severity": finding.severity,
                "action": finding.action,
                "path": finding.path,
                "line": finding.line,
            }
            for finding in report.ranked_findings
        ],
    }
    Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_baseline(path: str) -> set[str]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return {
        str(item["fingerprint"])
        for item in payload.get("findings", [])
        if item.get("fingerprint")
    }


def scan_report_to_json(report: ScanReport) -> str:
    return json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n"


def _scan_github_url(
    url: str,
    *,
    baseline: set[str],
    baseline_path: Optional[str],
) -> ScanReport:
    parsed = urlparse(url)
    parts = [part for part in parsed.path.strip("/").split("/") if part]
    if parsed.netloc.lower() != "github.com" or len(parts) < 2:
        raise ScanError("only public https://github.com/org/repo URLs are supported")
    if shutil.which("git") is None:
        raise ScanError("git is required to scan public GitHub repositories")

    repo_name = "/".join(parts[:2])
    clone_url = f"https://github.com/{repo_name}.git"
    with tempfile.TemporaryDirectory(prefix="agent-consistency-scan-") as tmp:
        target = Path(tmp) / parts[1]
        result = subprocess.run(
            ["git", "clone", "--depth", "1", "--quiet", clone_url, str(target)],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise ScanError(result.stderr.strip() or f"failed to clone {clone_url}")
        return scan_path(
            target,
            baseline=baseline,
            baseline_path=baseline_path,
            repository=repo_name,
            source=url,
        )


def _iter_source_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in SOURCE_EXTENSIONS:
            continue
        if any(marker in path.name.lower() for marker in TEST_FILE_MARKERS):
            continue
        if path.name.lower().startswith(DEV_FILE_MARKERS) or any(
            marker in path.name.lower() for marker in DEV_FILE_MARKERS[1:]
        ):
            continue
        try:
            relative = path.relative_to(root)
        except ValueError:
            relative = path
        if any(part in DEFAULT_EXCLUDED_DIRS for part in relative.parts[:-1]):
            continue
        if any(part.startswith(".") and part not in {".github"} for part in relative.parts[:-1]):
            continue
        yield path


def _scan_file(path: Path, root: Path) -> tuple[List[ScanFinding], int]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    lines = text.splitlines()
    if path.suffix.lower() == ".py":
        return _scan_python_file(path, root, lines, text)
    return _scan_text_file(path, root, lines)


def _scan_python_file(
    path: Path,
    root: Path,
    lines: List[str],
    text: str,
) -> tuple[List[ScanFinding], int]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return _scan_text_file(path, root, lines)

    findings: List[ScanFinding] = []
    verified = 0
    covered_lines: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        action = _risky_action_from_name(node.name)
        if not action or _is_suppressed(lines, node.lineno):
            continue
        if action in GENERIC_HELPER_ACTIONS:
            continue
        end_line = getattr(node, "end_lineno", node.lineno)
        context = _context(lines, node.lineno, end_line)
        if _should_ignore_action(action, context, _line(lines, node.lineno), kind="function"):
            continue
        if _has_outcome_protection(context):
            verified += 1
            continue
        finding = _build_finding(
            path,
            root,
            line=node.lineno,
            action=action,
            context=context,
            line_text=_line(lines, node.lineno),
            kind="function",
        )
        findings.append(finding)
        covered_lines.update(range(node.lineno, end_line + 1))

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        line = getattr(node, "lineno", 0) or 0
        if line in covered_lines or _is_suppressed(lines, line):
            continue
        action_name = _call_name(node)
        action = _risky_action_from_name(action_name)
        if not action:
            continue
        context = _context(lines, max(1, line - 6), min(len(lines), line + 6))
        if _should_ignore_action(action, context, _line(lines, line), kind="call"):
            continue
        if _has_outcome_protection(context):
            verified += 1
            continue
        finding = _build_finding(
            path,
            root,
            line=line,
            action=action,
            context=context,
            line_text=_line(lines, line),
            kind="call",
        )
        findings.append(finding)

    return _dedupe_findings(findings), verified


def _scan_text_file(path: Path, root: Path, lines: List[str]) -> tuple[List[ScanFinding], int]:
    findings: List[ScanFinding] = []
    verified = 0
    for index, line_text in enumerate(lines, start=1):
        if _is_suppressed(lines, index):
            continue
        action_source = _strip_string_literals(line_text)
        action = _risky_action_from_name(action_source)
        if not action:
            continue
        if not _looks_like_executable_text_line(action_source, action):
            continue
        context = _context(lines, max(1, index - 6), min(len(lines), index + 6))
        if _should_ignore_action(action, context, line_text, kind="pattern"):
            continue
        if _has_outcome_protection(context):
            verified += 1
            continue
        findings.append(
            _build_finding(
                path,
                root,
                line=index,
                action=action,
                context=context,
                line_text=line_text,
                kind="pattern",
            )
        )
    return _dedupe_findings(findings), verified


def _build_finding(
    path: Path,
    root: Path,
    *,
    line: int,
    action: str,
    context: str,
    line_text: str,
    kind: str,
) -> ScanFinding:
    action_key = _normalize(action)
    dangerous_message = _contains_any(context, DANGEROUS_MESSAGE_TERMS)
    has_idempotency = _contains_any(context, IDEMPOTENCY_TERMS)
    category = _category(action_key, context)
    severity = _severity(action_key, category, dangerous_message, has_idempotency)
    confidence = _confidence(action_key, category, dangerous_message, kind)
    evidence_found = [f"matched action `{action}`"]
    if dangerous_message:
        evidence_found.append("completion-like customer message text")
    if has_idempotency:
        evidence_found.append("idempotency term nearby")

    evidence_missing = ["confirmed outcome check"]
    if category in {"financial", "destructive", "trading"} and not has_idempotency:
        evidence_missing.append("idempotency key")
    if "handoff" in action_key:
        evidence_missing.append("handoff facts")

    why = _why(action, category, confidence)
    suggestion = _suggested_fix(action, category, needs_idempotency=not has_idempotency)
    snippet = _snippet(lines=context)
    relative = _relative_path(path, root)
    fingerprint = _fingerprint(relative, line_text, action, "risky_action_without_confirmation")
    return ScanFinding(
        severity=severity,
        confidence=confidence,
        path=relative,
        line=line,
        action=action,
        why=why,
        evidence_found=evidence_found,
        evidence_missing=evidence_missing,
        suggested_fix=suggestion,
        snippet=snippet,
        category=category,
        fingerprint=fingerprint,
    )


def _finding_markdown(finding: ScanFinding) -> List[str]:
    lines = [
        f"### {finding.severity.upper()} - `{finding.action}`",
        f"File: `{finding.path}:{finding.line}`",
        f"Confidence: `{finding.confidence}`",
        "",
    ]
    if finding.confidence == "low":
        lines.extend(["Possible risk, needs review.", ""])
    lines.extend(
        [
            finding.why,
            "",
            "Evidence found:",
            *[f"* {item}" for item in finding.evidence_found],
            "",
            "Evidence missing:",
            *[f"* {item}" for item in finding.evidence_missing],
            "",
            "Suggested fix:",
            "",
            "```python",
            finding.suggested_fix,
            "```",
            "",
            "Nearby code:",
            "",
            "```text",
            finding.snippet,
            "```",
        ]
    )
    return lines


def _finding_group_markdown(group: Dict[str, Any]) -> List[str]:
    representative = group["representative"]
    lines = [
        f"### {group['severity'].upper()} - `{group['action']}`",
        f"Category: `{group['category']}`",
        f"Occurrences: {group['count']}",
        f"Representative file: `{representative.path}:{representative.line}`",
        f"Confidence: `{group['confidence']}`",
        "",
    ]
    if group["confidence"] == "low":
        lines.extend(["Possible risk, needs review.", ""])
    lines.extend(
        [
            group["why"],
            "",
            "Evidence found:",
            *[f"* {item}" for item in group["evidence_found"]],
            "",
            "Evidence missing:",
            *[f"* {item}" for item in group["evidence_missing"]],
            "",
            "Suggested fix:",
            "",
            "```python",
            representative.suggested_fix,
            "```",
            "",
            "Representative code:",
            "",
            "```text",
            representative.snippet,
            "```",
        ]
    )
    if len(group["locations"]) > 1:
        lines.extend(
            ["", "Other locations:", *[f"* `{location}`" for location in group["locations"][1:6]]]
        )
    return lines


def _risky_action_from_name(value: str) -> Optional[str]:
    normalized = _normalize(value).strip("_")
    if "refund" in normalized and any(term in normalized for term in ("send", "email", "message")):
        return "send_refund_confirmation"
    for action in RISKY_ACTIONS:
        action_key = _normalize(action).strip("_")
        if "_" in action_key and action_key in normalized:
            return action
        if "_" not in action_key and _verb_token_present(normalized, action_key):
            return action
    return None


def _verb_token_present(normalized: str, action_key: str) -> bool:
    tokens = [token for token in normalized.split("_") if token]
    if action_key == "approve":
        return "approve" in tokens
    if action_key == "deploy":
        return any(token in {"deploy", "deploys", "deployed", "deploying"} for token in tokens)
    if action_key == "refund":
        return any(token in {"refund", "refunds", "refunded"} for token in tokens)
    if action_key == "provision":
        return any(
            token in {"provision", "provisions", "provisioned", "provisioning"}
            for token in tokens
        )
    return action_key in tokens


def _should_ignore_action(action: str, context: str, line_text: str, *, kind: str) -> bool:
    action_key = _normalize(action).strip("_")
    context_key = _normalize(context)
    line_key = _normalize(line_text)
    dangerous_message = _contains_any(context, DANGEROUS_MESSAGE_TERMS)
    customer_signal = _contains_any(context, CUSTOMER_TERMS)

    if action_key in {"send_message", "send_email", "notify_customer"}:
        if _contains_any(context, INTERNAL_MESSAGE_TERMS) and not customer_signal:
            return True
        if not dangerous_message and not customer_signal and "email" not in action_key:
            return True

    if action_key in {"approve", "deploy", "provision"} and kind == "pattern":
        if not re.search(r"\b(function|async|const|let|var|def|await|return)\b|[.(]", line_text):
            return True

    if action_key == "write_state" and "_write_state" in line_key and "state_file" in context_key:
        return True

    return False


def _looks_like_executable_text_line(line_text: str, action: str) -> bool:
    stripped = line_text.strip()
    if stripped.startswith(("import ", "from ", "export ", "//", "#")):
        return False
    action_key = _normalize(action).strip("_")
    if action_key in {"approve", "deploy", "provision", "refund"}:
        return bool(
            re.search(r"\b(function|async|const|let|var|def|await|return)\b|[.(]", line_text)
        )
    return True


def _category(action_key: str, context: str) -> str:
    context_key = _normalize(context)
    if "refund" in action_key or "refund" in context_key:
        return "financial"
    if any(term in action_key for term in ("delete", "remove", "cancel")):
        return "destructive"
    if any(term in action_key for term in ("grant", "access", "assign_role")):
        return "access_control"
    if "ticket" in action_key or "resolved" in context_key:
        return "support"
    if any(term in action_key for term in ("trade", "order")) or "order_filled" in context_key:
        return "trading"
    if any(term in action_key for term in ("email", "message", "notify", "send")):
        return "customer_visible"
    if any(term in action_key for term in ("deploy", "provision", "write", "update", "approve")):
        return "production_state"
    return "ambiguous"


def _severity(
    action_key: str,
    category: str,
    dangerous_message: bool,
    has_idempotency: bool,
) -> str:
    if category in {"financial", "destructive", "access_control", "support", "trading"}:
        if has_idempotency and category in {"financial", "destructive", "trading"}:
            return "medium"
        return "high"
    if category == "customer_visible" and dangerous_message:
        return "high"
    if category in {"customer_visible", "production_state"}:
        return "medium"
    if "notify" in action_key:
        return "low"
    return "low"


def _confidence(action_key: str, category: str, dangerous_message: bool, kind: str) -> str:
    if dangerous_message and category in {"financial", "customer_visible", "support", "trading"}:
        return "high"
    if category in {"destructive", "access_control"}:
        return "high" if kind == "call" else "medium"
    if category in {"financial", "support", "trading"}:
        return "medium"
    if category == "production_state" and kind in {"function", "call"}:
        return "medium"
    return "low"


def _why(action: str, category: str, confidence: str) -> str:
    prefix = "Possible risk, needs review. " if confidence == "low" else ""
    reasons = {
        "financial": (
            f"{action} may claim completion before settlement or provider confirmation is found."
        ),
        "destructive": (
            f"{action} is destructive and no nearby idempotency plus deletion "
            "confirmation was found."
        ),
        "access_control": (
            f"{action} changes access or roles without a nearby correctness confirmation."
        ),
        "support": (
            f"{action} may mark work resolved before resolution evidence is confirmed."
        ),
        "trading": (
            f"{action} may report an order as complete before broker fill confirmation is found."
        ),
        "customer_visible": (
            f"{action} may send a customer-visible completion claim before the outcome is verified."
        ),
        "production_state": (
            f"{action} changes production state without a nearby read-after-write or outcome check."
        ),
    }
    return prefix + reasons.get(category, f"{action} may be risky but needs manual review.")


def _suggested_fix(action: str, category: str, *, needs_idempotency: bool) -> str:
    criticality = "financial" if category in {"financial", "trading"} else (
        "irreversible" if category in {"destructive", "access_control"} else "high"
    )
    outcome = {
        "financial": "refund_settled",
        "destructive": "deletion_confirmed",
        "access_control": "access_grant_verified",
        "support": "resolution_confirmed",
        "trading": "order_filled",
        "customer_visible": "customer_claim_supported",
        "production_state": "read_after_write_confirmed",
    }.get(category, "outcome_verified")
    idempotency_line = ",\n    idempotency_key=request_id" if needs_idempotency else ""
    return (
        "with reliability_gate(\n"
        "    run,\n"
        '    "scanner",\n'
        f'    "{action}",\n'
        f'    criticality="{criticality}"'
        f"{idempotency_line},\n"
        ") as gate:\n"
        f'    gate.step.verify_outcome("{outcome}", lambda: status_is_confirmed())\n'
        "    # perform or continue the action only after the outcome check is true"
    )


def _call_name(node: ast.Call) -> str:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return ""


def _has_outcome_protection(context: str) -> bool:
    normalized = context.lower()
    return _contains_any(normalized, PROTECTION_TERMS) or _contains_any(normalized, OUTCOME_TERMS)


def _contains_any(value: str, terms: Iterable[str]) -> bool:
    lowered = value.lower()
    return any(term.lower() in lowered for term in terms)


def _strip_string_literals(value: str) -> str:
    without_strings = re.sub(r"(['\"])(?:\\.|(?!\1).)*\1", "", value)
    return re.sub(r">\s*[^<{}()=]+\s*<", "><", without_strings)


def _token_or_phrase_present(normalized: str, term: str) -> bool:
    if "_" in term:
        return term in normalized
    return term in {token for token in normalized.split("_") if token}


def _is_suppressed(lines: List[str], line: int) -> bool:
    if line <= 0:
        return False
    start = max(1, line - 2)
    text = "\n".join(_line(lines, index) for index in range(start, line + 1))
    return SUPPRESSION_MARKER in text


def _context(lines: List[str], start: int, end: int) -> str:
    start = max(1, start)
    end = min(len(lines), end)
    return "\n".join(_line(lines, index) for index in range(start, end + 1))


def _line(lines: List[str], line: int) -> str:
    if 1 <= line <= len(lines):
        return lines[line - 1]
    return ""


def _snippet(lines: str) -> str:
    snippet_lines = lines.strip().splitlines()
    return "\n".join(snippet_lines[:8])


def _relative_path(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _repository_name(path: Path) -> str:
    resolved = path.resolve()
    return resolved.name if resolved.is_dir() else resolved.parent.name


def _finding_groups(findings: Iterable[ScanFinding]) -> List[Dict[str, Any]]:
    grouped: Dict[tuple[str, str, str], List[ScanFinding]] = {}
    for finding in findings:
        key = (finding.category, finding.action, "|".join(sorted(finding.evidence_missing)))
        grouped.setdefault(key, []).append(finding)

    groups: List[Dict[str, Any]] = []
    for (category, action, _missing), items in grouped.items():
        ordered = sorted(
            items,
            key=lambda finding: (
                SEVERITY_ORDER.get(finding.severity, 99),
                CONFIDENCE_ORDER.get(finding.confidence, 99),
                finding.path,
                finding.line,
            ),
        )
        representative = ordered[0]
        severity = min((item.severity for item in ordered), key=lambda value: SEVERITY_ORDER[value])
        confidence = min(
            (item.confidence for item in ordered),
            key=lambda value: CONFIDENCE_ORDER.get(value, 99),
        )
        evidence_found = sorted({item for finding in ordered for item in finding.evidence_found})
        evidence_missing = sorted(
            {item for finding in ordered for item in finding.evidence_missing}
        )
        locations = [f"{finding.path}:{finding.line}" for finding in ordered]
        groups.append(
            {
                "category": category,
                "action": action,
                "severity": severity,
                "confidence": confidence,
                "count": len(ordered),
                "why": representative.why,
                "evidence_found": evidence_found,
                "evidence_missing": evidence_missing,
                "locations": locations,
                "representative": representative,
            }
        )

    return sorted(
        groups,
        key=lambda group: (
            SEVERITY_ORDER.get(group["severity"], 99),
            CONFIDENCE_ORDER.get(group["confidence"], 99),
            -int(group["count"]),
            group["action"],
        ),
    )


def _finding_group_to_dict(group: Dict[str, Any]) -> Dict[str, Any]:
    representative = group["representative"]
    return {
        "category": group["category"],
        "action": group["action"],
        "severity": group["severity"],
        "confidence": group["confidence"],
        "count": group["count"],
        "why": group["why"],
        "evidence_found": list(group["evidence_found"]),
        "evidence_missing": list(group["evidence_missing"]),
        "locations": list(group["locations"]),
        "representative": representative.to_dict(),
    }


def _dedupe_findings(findings: Iterable[ScanFinding]) -> List[ScanFinding]:
    seen: set[str] = set()
    deduped: List[ScanFinding] = []
    for finding in findings:
        if finding.fingerprint in seen:
            continue
        seen.add(finding.fingerprint)
        deduped.append(finding)
    return deduped


def _fingerprint(path: str, line_text: str, action: str, rule: str) -> str:
    stable = "|".join([path, _normalize(line_text), action, rule])
    return hashlib.sha256(stable.encode("utf-8")).hexdigest()[:16]


def _normalize(value: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in value)


def _is_github_url(target: str) -> bool:
    parsed = urlparse(target)
    return parsed.scheme in {"http", "https"} and parsed.netloc.lower() == "github.com"
