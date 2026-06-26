import argparse
import importlib.resources
import sys
from typing import List, Optional

from .detect import detect_receipt_file, render_risk_report
from .receipt_verification import render_verify_report, verify_receipt_file
from .reporting import (
    load_receipt_report,
    render_text_summary,
    summarize_report,
    write_html_summary,
)
from .scanner import (
    ScanError,
    render_scan_markdown,
    render_scan_text,
    scan_report_to_json,
    scan_target,
    write_baseline,
)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="agent-consistency",
        description="Validate and summarize agent-consistency receipt reports.",
    )
    subparsers = parser.add_subparsers(dest="command")

    report_parser = subparsers.add_parser("report", help="summarize a receipt file or run dir")
    report_parser.add_argument("path", help="path to summary.json, receipts.jsonl, or run dir")
    report_parser.add_argument("--html", help="optional path to write an HTML summary")

    verify_parser = subparsers.add_parser(
        "verify",
        help="verify receipt JSONL structure, references, and digest chain",
    )
    verify_parser.add_argument("path", help="path to receipts.jsonl")

    detect_parser = subparsers.add_parser(
        "detect",
        help="detect false-success risk in a receipt JSONL file or run dir",
    )
    detect_parser.add_argument("path", help="path to summary.json, receipts.jsonl, or run dir")

    scan_parser = subparsers.add_parser(
        "scan",
        help="scan source code for false-success risks before runtime integration",
    )
    scan_parser.add_argument("target", help="local path or public https://github.com/org/repo URL")
    scan_parser.add_argument(
        "--format",
        choices=["text", "json", "markdown"],
        default="text",
        help="report format",
    )
    scan_parser.add_argument(
        "--fail-on",
        choices=["high", "medium", "low"],
        help="exit non-zero when findings at this severity or above are present",
    )
    scan_parser.add_argument(
        "--baseline",
        help="suppress findings whose fingerprints are in this baseline file",
    )
    scan_parser.add_argument(
        "--write-baseline",
        action="store_true",
        help="write current findings to agent-consistency-baseline.json",
    )

    subparsers.add_parser("schema", help="print the receipt JSON Schema")

    args = parser.parse_args(argv)
    if args.command == "report":
        try:
            report = load_receipt_report(args.path)
        except Exception as exc:
            sys.stderr.write(f"Error: {exc}\n")
            return 1
        summary = summarize_report(report)
        sys.stdout.write(render_text_summary(summary))
        if args.html:
            write_html_summary(summary, args.html)
            sys.stdout.write(f"HTML report: {args.html}\n")
        return 0

    if args.command == "verify":
        verification_report = verify_receipt_file(args.path)
        sys.stdout.write(render_verify_report(verification_report))
        return 0 if verification_report.ok else 1

    if args.command == "detect":
        try:
            risk_report = detect_receipt_file(args.path)
        except Exception as exc:
            sys.stderr.write(f"Error: {exc}\n")
            return 1
        sys.stdout.write(render_risk_report(risk_report))
        return 1 if risk_report.has_high_severity else 0

    if args.command == "scan":
        try:
            scan_report = scan_target(args.target, baseline_path=args.baseline)
        except (OSError, ScanError, ValueError) as exc:
            sys.stderr.write(f"Error: {exc}\n")
            return 1
        if args.format == "json":
            sys.stdout.write(scan_report_to_json(scan_report))
        elif args.format == "markdown":
            sys.stdout.write(render_scan_markdown(scan_report))
        else:
            sys.stdout.write(render_scan_text(scan_report))
        if args.write_baseline:
            write_baseline(scan_report)
            sys.stdout.write("Baseline written: agent-consistency-baseline.json\n")
        if args.fail_on and scan_report.has_severity_at_or_above(args.fail_on):
            return 1
        return 0

    if args.command == "schema":
        schema = importlib.resources.files("agent_consistency.schemas").joinpath(
            "receipt.schema.json"
        )
        text = schema.read_text(encoding="utf-8")
        sys.stdout.write(text)
        if not text.endswith("\n"):
            sys.stdout.write("\n")
        return 0

    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
