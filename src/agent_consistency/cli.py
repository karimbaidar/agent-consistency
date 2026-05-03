import argparse
import sys
from typing import List, Optional

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

    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
