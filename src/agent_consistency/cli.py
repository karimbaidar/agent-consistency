import argparse
import importlib.resources
import sys
from typing import List, Optional

from .receipt_verification import render_verify_report, verify_receipt_file
from .reporting import (
    load_receipt_report,
    render_text_summary,
    summarize_report,
    write_html_summary,
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
