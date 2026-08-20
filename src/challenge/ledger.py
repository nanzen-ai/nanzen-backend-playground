"""Accounts receivable: what each customer still owes us.

The account team reads these numbers straight off the customer page before a
renewal conversation, so they end up in front of the customer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from sqlite3 import Connection, Row


@dataclass
class InvoiceLine:
    invoice_id: str
    due_date: str
    total_amount: float
    amount_paid: float
    status: str

    @property
    def outstanding(self) -> float:
        return round(self.total_amount - self.amount_paid, 2)


@dataclass
class CustomerSummary:
    customer_id: str
    name: str
    currency: str
    total_invoiced: float
    total_received: float
    outstanding: float
    invoices: list[InvoiceLine] = field(default_factory=list)


def _customer(conn: Connection, customer_id: str) -> Row | None:
    return conn.execute("SELECT * FROM customers WHERE customer_id = ?", (customer_id,)).fetchone()


def total_invoiced(conn: Connection, customer_id: str) -> float:
    row = conn.execute(
        "SELECT COALESCE(SUM(total_amount), 0) AS total FROM invoices WHERE customer_id = ?",
        (customer_id,),
    ).fetchone()
    return round(row["total"], 2)


def total_received(conn: Connection, customer_id: str) -> float:
    row = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) AS total FROM payments WHERE customer_id = ?",
        (customer_id,),
    ).fetchone()
    return round(row["total"], 2)


def outstanding(conn: Connection, customer_id: str) -> float:
    """How much this customer still owes, across every invoice that is not settled."""
    row = conn.execute(
        "SELECT COALESCE(SUM(total_amount - amount_paid), 0) AS total "
        "FROM invoices WHERE customer_id = ? AND status != 'paid'",
        (customer_id,),
    ).fetchone()
    return round(row["total"], 2)


def invoice_lines(conn: Connection, customer_id: str) -> list[InvoiceLine]:
    rows = conn.execute(
        "SELECT * FROM invoices WHERE customer_id = ? ORDER BY due_date",
        (customer_id,),
    ).fetchall()
    return [
        InvoiceLine(
            invoice_id=r["invoice_id"],
            due_date=r["due_date"],
            total_amount=r["total_amount"],
            amount_paid=r["amount_paid"],
            status=r["status"],
        )
        for r in rows
    ]


def customer_summary(conn: Connection, customer_id: str) -> CustomerSummary | None:
    customer = _customer(conn, customer_id)
    if customer is None:
        return None

    return CustomerSummary(
        customer_id=customer["customer_id"],
        name=customer["name"],
        currency=customer["currency"],
        total_invoiced=total_invoiced(conn, customer_id),
        total_received=total_received(conn, customer_id),
        outstanding=outstanding(conn, customer_id),
        invoices=invoice_lines(conn, customer_id),
    )


def unmatched_payments(conn: Connection, customer_id: str | None = None) -> list[Row]:
    """Payments the matcher could not place against an invoice."""
    if customer_id:
        return conn.execute(
            "SELECT * FROM payments WHERE matched_at IS NULL AND customer_id = ? "
            "ORDER BY value_date",
            (customer_id,),
        ).fetchall()
    return conn.execute(
        "SELECT * FROM payments WHERE matched_at IS NULL ORDER BY value_date"
    ).fetchall()
