import json
import sys
import tempfile
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from .scanner import (
    ScanError,
    ScanFinding,
    ScanReport,
    render_scan_markdown,
    scan_path,
    scan_target,
)

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765

BUILT_IN_SCENARIO = """\
def call_provider(order_id):
    provider_response = {"status": "pending", "provider_id": "rf_123"}
    return provider_response


def send_refund_confirmation(customer_email, provider_response):
    send_email(
        customer_email,
        "Your refund is complete.",
        metadata={"provider_id": provider_response["provider_id"]},
    )
"""


def scan_built_in_scenario() -> ScanReport:
    with tempfile.TemporaryDirectory(prefix="agent-consistency-lab-") as tmp:
        root = Path(tmp) / "refund-agent"
        root.mkdir()
        (root / "agent.py").write_text(BUILT_IN_SCENARIO, encoding="utf-8")
        return scan_path(
            root,
            repository="built-in/refund-agent",
            source="built-in://refund-pending",
        )


def build_lab_response(report: ScanReport) -> Dict[str, Any]:
    top = report.ranked_findings[0] if report.findings else None
    return {
        "card": {
            "repository": report.repository,
            "risk_score": report.risk_score,
            "confidence": report.confidence,
            "risky_actions_found": report.risky_actions_found,
            "high_severity": report.high_severity,
            "medium_severity": report.medium_severity,
            "low_severity": report.low_severity,
            "false_success_exposure": report.false_success_exposure,
            "verified_actions_found": report.verified_actions_found,
            "idempotency_gaps": report.idempotency_gaps,
            "missing_outcome_checks": report.missing_outcome_checks,
            "top_finding": _finding_card(top),
            "honesty_note": _honesty_note(report),
            "gate_label": _gate_label(report),
            "gate_detail": _gate_detail(report),
        },
        "report": report.to_dict(),
        "markdown": render_scan_markdown(report),
    }


def run_lab_server(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
    server = ThreadingHTTPServer((host, port), LabRequestHandler)
    url = f"http://{host}:{port}"
    sys.stdout.write(f"False Success Lab running at {url}\n")
    sys.stdout.write("Press Ctrl+C to stop.\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        sys.stdout.write("\nStopping False Success Lab.\n")
    finally:
        server.server_close()


class LabRequestHandler(BaseHTTPRequestHandler):
    server_version = "AgentConsistencyLab/1.0"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        route = parsed.path
        if route == "/":
            route = "/index.html"
        self._serve_static(route.lstrip("/"))

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/scenario":
            self._handle_scenario()
            return
        if parsed.path == "/api/scan":
            self._handle_scan()
            return
        self._send_json({"error": "not found"}, status=HTTPStatus.NOT_FOUND)

    def log_message(self, format: str, *args: Any) -> None:
        sys.stderr.write("lab: " + format % args + "\n")

    def _handle_scenario(self) -> None:
        report = scan_built_in_scenario()
        self._send_json(build_lab_response(report))

    def _handle_scan(self) -> None:
        try:
            payload = self._read_json()
            target = str(payload.get("target", "")).strip()
            mode = str(payload.get("mode", "")).strip()
            if not target:
                raise ValueError("Enter a repo path or public GitHub URL.")
            if mode == "github" and not target.startswith("https://github.com/"):
                raise ValueError("Public repo scans currently support https://github.com/org/repo.")
            report = scan_target(target)
        except (OSError, ScanError, ValueError, json.JSONDecodeError) as exc:
            self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return
        self._send_json(build_lab_response(report))

    def _read_json(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        data = self.rfile.read(length)
        if not data:
            return {}
        payload = json.loads(data.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Expected a JSON object.")
        return payload

    def _serve_static(self, path: str) -> None:
        parts = Path(path).parts
        if ".." in parts:
            self._send_text("not found", status=HTTPStatus.NOT_FOUND)
            return
        resource = resources.files("agent_consistency").joinpath("lab_static")
        for part in parts:
            resource = resource.joinpath(part)
        if not resource.is_file():
            resource = (
                resources.files("agent_consistency").joinpath("lab_static").joinpath("index.html")
            )
        content_type = _content_type(str(resource))
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.end_headers()
        self.wfile.write(resource.read_bytes())

    def _send_json(self, payload: Dict[str, Any], *, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_text(self, text: str, *, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _finding_card(finding: Optional[ScanFinding]) -> Optional[Dict[str, Any]]:
    if finding is None:
        return None
    return {
        "severity": finding.severity,
        "confidence": finding.confidence,
        "path": finding.path,
        "line": finding.line,
        "action": finding.action,
        "why": finding.why,
        "evidence_found": finding.evidence_found,
        "evidence_missing": finding.evidence_missing,
        "suggested_fix": finding.suggested_fix,
    }


def _honesty_note(report: ScanReport) -> str:
    if any(finding.confidence == "low" for finding in report.findings):
        return "Possible risk, needs review."
    if report.findings:
        return "Findings are heuristic. Review the code path before treating them as certain bugs."
    return "No configured finding fired. This is a static scan, not a proof of safety."


def _gate_label(report: ScanReport) -> str:
    if report.high_severity:
        return "BLOCK"
    if report.findings:
        return "REVIEW"
    return "ALLOW"


def _gate_detail(report: ScanReport) -> str:
    if report.high_severity:
        return (
            "High-risk false-success exposure found. "
            "Do not continue until evidence checks are added."
        )
    if report.findings:
        return (
            "Review lower-confidence or partial-risk findings before claiming the workflow is done."
        )
    return (
        "No configured static finding fired. Runtime gates are still needed for production actions."
    )


def _content_type(path: str) -> str:
    suffix = Path(path).suffix.lower()
    return {
        ".css": "text/css; charset=utf-8",
        ".html": "text/html; charset=utf-8",
        ".js": "text/javascript; charset=utf-8",
        ".json": "application/json; charset=utf-8",
        ".svg": "image/svg+xml",
    }.get(suffix, "application/octet-stream")
