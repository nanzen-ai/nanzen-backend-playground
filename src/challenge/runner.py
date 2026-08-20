"""Command line entry point.

make reset                              rebuild the database from data/
make run ARGS="import"                  import every bank file, then match
make run ARGS="import 2026-02-16"       import one night's bank file
make run ARGS="report MERID-001"        print a customer's AR position
"""

from __future__ import annotations

import argparse
import sys

from challenge import ledger
from challenge.importer import import_payments, load_reference_data
from challenge.matcher import run_matching
from challenge.store import DATA_DIR, connect, drop_all


def cmd_reset() -> None:
    drop_all()
    conn = connect()
    try:
        load_reference_data(conn)
        count = conn.execute("SELECT COUNT(*) AS n FROM invoices").fetchone()["n"]
        print(f"database rebuilt, {count} invoices loaded, no payments imported yet")
    finally:
        conn.close()


def cmd_import(dates: list[str]) -> None:
    files = sorted(DATA_DIR.glob("payments_*.csv"))
    if dates:
        wanted = {f"payments_{d}.csv" for d in dates}
        files = [f for f in files if f.name in wanted]
        if not files:
            print(f"no bank files found for {', '.join(dates)}", file=sys.stderr)
            raise SystemExit(1)

    conn = connect()
    try:
        for path in files:
            print(import_payments(conn, path))
        print(run_matching(conn))
    finally:
        conn.close()


def cmd_report(customer_id: str) -> None:
    conn = connect()
    try:
        summary = ledger.customer_summary(conn, customer_id)
        if summary is None:
            print(f"unknown customer {customer_id}", file=sys.stderr)
            raise SystemExit(1)

        print(f"\n{summary.name} ({summary.customer_id})")
        print(f"  total invoiced   {summary.total_invoiced:>12,.2f} {summary.currency}")
        print(f"  total received   {summary.total_received:>12,.2f} {summary.currency}")
        print(f"  outstanding      {summary.outstanding:>12,.2f} {summary.currency}")
        print()
        print(f"  {'invoice':<18} {'due':<12} {'total':>10} {'paid':>10} {'status':<8}")
        for line in summary.invoices:
            print(
                f"  {line.invoice_id:<18} {line.due_date:<12} "
                f"{line.total_amount:>10,.2f} {line.amount_paid:>10,.2f} {line.status:<8}"
            )

        pending = ledger.unmatched_payments(conn, customer_id)
        print(f"\n  {len(pending)} payment(s) not matched to any invoice\n")
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(prog="challenge")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("reset", help="rebuild the database from data/")

    p_import = sub.add_parser("import", help="import bank files and run matching")
    p_import.add_argument("dates", nargs="*", help="e.g. 2026-02-16 (default: all files)")

    p_report = sub.add_parser("report", help="print a customer's AR position")
    p_report.add_argument("customer_id")

    args = parser.parse_args()

    if args.command == "reset":
        cmd_reset()
    elif args.command == "import":
        cmd_import(args.dates)
    elif args.command == "report":
        cmd_report(args.customer_id)


if __name__ == "__main__":
    main()
