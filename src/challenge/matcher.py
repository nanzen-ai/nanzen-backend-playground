"""Matching bank payments to invoices.

A payment is matched to an invoice in one of two ways:

  1. The remittance information names an invoice. Customers who use our
     payment instructions properly quote the invoice number, and this is by
     far the most common case.
  2. Nothing is quoted, so we fall back to the amount: the oldest open
     invoice for that customer billed for exactly what arrived.

Anything we cannot place is left alone for someone to look at.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from sqlite3 import Connection, Row


@dataclass
class MatchResult:
    considered: int
    matched: int
    unmatched: int

    def __str__(self) -> str:
        return (
            f"matching: {self.considered} payments considered, "
            f"{self.matched} matched, {self.unmatched} left unmatched"
        )


def _pending_payments(conn: Connection) -> list[Row]:
    """Payments the matcher has not looked at yet."""
    return conn.execute(
        "SELECT * FROM payments WHERE matched_at IS NULL ORDER BY value_date, bank_reference"
    ).fetchall()


def _open_invoices(conn: Connection, customer_id: str) -> list[Row]:
    return conn.execute(
        "SELECT * FROM invoices WHERE customer_id = ? AND status = 'open' ORDER BY due_date",
        (customer_id,),
    ).fetchall()


def find_invoice_for(conn: Connection, payment: Row) -> Row | None:
    """Work out which invoice a payment settles, or None if we cannot tell."""
    open_invoices = _open_invoices(conn, payment["customer_id"])
    remittance = (payment["remittance_info"] or "").upper()

    # 1. The customer quoted an invoice number.
    for invoice in open_invoices:
        if invoice["invoice_id"].upper() in remittance:
            return invoice

    # 2. Nothing quoted: fall back to the amount.
    for invoice in open_invoices:
        if invoice["total_amount"] == payment["amount"]:
            return invoice

    return None


def apply_payment(conn: Connection, payment: Row, invoice: Row) -> None:
    """Record that this payment settles (part of) this invoice."""
    amount_paid = round(invoice["amount_paid"] + payment["amount"], 2)
    status = "paid" if amount_paid >= invoice["total_amount"] else "open"

    conn.execute(
        "UPDATE invoices SET amount_paid = ?, status = ? WHERE invoice_id = ?",
        (amount_paid, status, invoice["invoice_id"]),
    )


def run_matching(conn: Connection) -> MatchResult:
    """Run the matcher over every payment that has not been through it yet."""
    payments = _pending_payments(conn)
    matched = 0
    now = datetime.now(timezone.utc).isoformat()

    for payment in payments:
        invoice = find_invoice_for(conn, payment)
        if invoice is None:
            continue

        apply_payment(conn, payment, invoice)
        conn.execute(
            "UPDATE payments SET matched_at = ? WHERE bank_reference = ?",
            (now, payment["bank_reference"]),
        )
        matched += 1

    conn.commit()
    return MatchResult(
        considered=len(payments),
        matched=matched,
        unmatched=len(payments) - matched,
    )
