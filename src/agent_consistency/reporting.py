import html
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping


def load_receipt_report(path: str) -> Dict[str, Any]:
    source = Path(path)
    if source.is_dir():
        summary = source / "summary.json"
        receipts = source / "receipts.jsonl"
        if summary.exists():
            return _load_json_report(summary)
        if receipts.exists():
            return _report_from_receipts(_load_jsonl_receipts(receipts), source=str(receipts))
        raise FileNotFoundError(f"no summary.json or receipts.jsonl found in {source}")
    if source.suffix == ".jsonl":
        return _report_from_receipts(_load_jsonl_receipts(source), source=str(source))
    return _load_json_report(source)


def summarize_report(report: Mapping[str, Any]) -> Dict[str, Any]:
    receipts = list(report.get("receipts") or [])
    steps = [_step_summary(receipt) for receipt in receipts]
    failed_steps = [step for step in steps if step["status"] == "failed"]
    issues = [
        {"step_id": step["step_id"], **issue}
        for step in steps
        for issue in step["issues"]
    ]
    outcomes = [
        {"step_id": step["step_id"], **outcome}
        for step in steps
        for outcome in step["outcomes"]
    ]
    status = str(report.get("status") or ("failed" if failed_steps else "passed"))
    return {
        "run_id": str(report.get("run_id") or _infer_run_id(receipts)),
        "status": status,
        "provider": report.get("provider"),
        "scenario": report.get("scenario"),
        "receipt_count": len(receipts),
        "failed_step_count": len(failed_steps),
        "issue_count": len(issues),
        "outcome_count": len(outcomes),
        "steps": steps,
        "issues": issues,
        "outcomes": outcomes,
        "source": report.get("source"),
    }


def render_text_summary(summary: Mapping[str, Any]) -> str:
    lines = [
        f"Run: {summary['run_id']}",
        f"Status: {str(summary['status']).upper()}",
        f"Receipts: {summary['receipt_count']}",
    ]
    if summary.get("scenario"):
        lines.append(f"Scenario: {summary['scenario']}")
    if summary.get("provider"):
        lines.append(f"Provider: {summary['provider']}")
    lines.append("")
    lines.append("Steps:")
    for step in summary.get("steps") or []:
        lines.append(
            f"- {step['step_id']} {step['agent']}::{step['action']} "
            f"[{str(step['status']).upper()}]"
        )
        for issue in step["issues"]:
            lines.append(f"  issue: {issue['code']} - {issue['message']}")
        for outcome in step["outcomes"]:
            state = "passed" if outcome["passed"] else "failed"
            reason = f" - {outcome['reason']}" if outcome.get("reason") else ""
            lines.append(f"  outcome: {outcome['name']} {state}{reason}")
    if not summary.get("steps"):
        lines.append("- no receipts found")
    return "\n".join(lines) + "\n"


def write_html_summary(summary: Mapping[str, Any], path: str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(_render_html(summary), encoding="utf-8")


def _load_json_report(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return _report_from_receipts(payload, source=str(path))
    if "receipts" in payload:
        report = dict(payload)
        report["source"] = str(path)
        return report
    return _report_from_receipts([payload], source=str(path))


def _load_jsonl_receipts(path: Path) -> List[Dict[str, Any]]:
    receipts: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                receipts.append(json.loads(line))
    return receipts


def _report_from_receipts(receipts: Iterable[Mapping[str, Any]], *, source: str) -> Dict[str, Any]:
    receipt_list = [dict(receipt) for receipt in receipts]
    failed = any(receipt.get("status") == "failed" for receipt in receipt_list)
    return {
        "run_id": _infer_run_id(receipt_list),
        "status": "failed" if failed else "passed",
        "receipt_count": len(receipt_list),
        "receipts": receipt_list,
        "source": source,
    }


def _infer_run_id(receipts: Iterable[Mapping[str, Any]]) -> str:
    for receipt in receipts:
        if receipt.get("run_id"):
            return str(receipt["run_id"])
    return "unknown-run"


def _step_summary(receipt: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "step_id": str(receipt.get("step_id") or "unknown-step"),
        "agent": str(receipt.get("agent") or "unknown-agent"),
        "action": str(receipt.get("action") or "unknown-action"),
        "status": str(receipt.get("status") or "unknown"),
        "issues": [
            {
                "code": str(issue.get("code") or "issue"),
                "message": str(issue.get("message") or ""),
                "severity": str(issue.get("severity") or "error"),
            }
            for issue in receipt.get("issues") or []
        ],
        "outcomes": [
            {
                "name": str(outcome.get("name") or "outcome"),
                "passed": bool(outcome.get("passed")),
                "reason": str(outcome.get("reason") or ""),
            }
            for outcome in receipt.get("outcomes") or []
        ],
    }


def _render_html(summary: Mapping[str, Any]) -> str:
    rows = "\n".join(_step_row(step) for step in summary.get("steps") or [])
    if not rows:
        rows = "<tr><td colspan=\"4\">No receipts found.</td></tr>"
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(str(summary['run_id']))} agent-consistency report</title>
  <style>
    body {{
      margin: 0;
      background: #f4f7f8;
      color: #17202e;
      font: 14px/1.45 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    main {{ max-width: 980px; margin: 0 auto; padding: 32px 18px; }}
    header, section {{
      background: #ffffff;
      border: 1px solid #d7dee9;
      border-radius: 8px;
      padding: 16px;
      margin-bottom: 14px;
    }}
    h1, h2, p {{ margin: 0; }}
    h1 {{ font-size: 28px; }}
    p {{ color: #647084; margin-top: 6px; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 12px; }}
    th, td {{ text-align: left; padding: 10px; border-bottom: 1px solid #d7dee9; }}
    th {{ color: #647084; font-size: 12px; text-transform: uppercase; }}
    .passed {{ color: #18764b; font-weight: 800; }}
    .failed {{ color: #ba2b24; font-weight: 800; }}
  </style>
</head>
<body>
<main>
  <header>
    <h1>{html.escape(str(summary['run_id']))}</h1>
    <p>Status: <span class="{html.escape(str(summary['status']))}">
      {html.escape(str(summary['status']).upper())}
    </span></p>
    <p>Receipts: {html.escape(str(summary['receipt_count']))}</p>
  </header>
  <section>
    <h2>Steps</h2>
    <table>
      <thead>
        <tr><th>Step</th><th>Agent</th><th>Status</th><th>Issues and outcomes</th></tr>
      </thead>
      <tbody>
        {rows}
      </tbody>
    </table>
  </section>
</main>
</body>
</html>"""


def _step_row(step: Mapping[str, Any]) -> str:
    details = []
    for issue in step.get("issues") or []:
        details.append(f"issue: {issue['code']} - {issue['message']}")
    for outcome in step.get("outcomes") or []:
        state = "passed" if outcome["passed"] else "failed"
        details.append(f"outcome: {outcome['name']} {state}")
    detail_text = "<br>".join(html.escape(item) for item in details) or "None"
    status = str(step["status"])
    return (
        "<tr>"
        f"<td>{html.escape(str(step['step_id']))}</td>"
        f"<td>{html.escape(str(step['agent']))}</td>"
        f"<td class=\"{html.escape(status)}\">{html.escape(status.upper())}</td>"
        f"<td>{detail_text}</td>"
        "</tr>"
    )
