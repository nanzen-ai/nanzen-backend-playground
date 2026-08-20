"""Tests for payment matching."""

from datetime import datetime, timezone

import pytest

from challenge.ledger import customer_summary
from challenge.matcher import run_matching
from challenge.store import connect


@pytest.fixture
def conn(tmp_path):
    connection = connect(tmp_path / "test.db")
    connection.execute(
        "INSERT INTO customers (customer_id, name, country, currency) "
        "VALUES ('ACME-001', 'Acme BV', 'NL', 'EUR')"
    )
    yield connection
    connection.close()


def add_invoice(conn, invoice_id, amount, due_date="2026-03-01"):
    conn.execute(
        "INSERT INTO invoices "
        "(invoice_id, customer_id, issue_date, due_date, total_amount, currency) "
        "VALUES (?, 'ACME-001', '2026-02-01', ?, ?, 'EUR')",
        (invoice_id, due_date, amount),
    )


def add_payment(conn, reference, amount, remittance=""):
    conn.execute(
        "INSERT INTO payments "
        "(bank_reference, customer_id, value_date, amount, currency, "
        " remittance_info, source_file, imported_at) "
        "VALUES (?, 'ACME-001', '2026-02-15', ?, 'EUR', ?, 'test.csv', ?)",
        (reference, amount, remittance, datetime.now(timezone.utc).isoformat()),
    )


class TestMatching:
    def test_matches_invoice_quoted_in_remittance(self, conn):
        add_invoice(conn, "INV-001", 1000.00)
        add_payment(conn, "BANK-1", 1000.00, "ACME BV INV-001")

        result = run_matching(conn)

        assert result.matched == 1
        summary = customer_summary(conn, "ACME-001")
        assert summary.outstanding == 0.00

    def test_falls_back_to_amount_when_nothing_quoted(self, conn):
        add_invoice(conn, "INV-001", 1000.00)
        add_payment(conn, "BANK-1", 1000.00, "ACME BV")

        result = run_matching(conn)

        assert result.matched == 1
        summary = customer_summary(conn, "ACME-001")
        assert summary.invoices[0].status == "paid"

    def test_leaves_payment_unmatched_when_no_invoice_fits(self, conn):
        add_invoice(conn, "INV-001", 1000.00)
        add_payment(conn, "BANK-1", 250.00, "ACME BV")

        result = run_matching(conn)

        assert result.matched == 0
        assert result.unmatched == 1

    def test_outstanding_reflects_unpaid_invoices(self, conn):
        add_invoice(conn, "INV-001", 1000.00, due_date="2026-03-01")
        add_invoice(conn, "INV-002", 250.00, due_date="2026-03-15")
        add_payment(conn, "BANK-1", 1000.00, "ACME BV INV-001")

        run_matching(conn)

        summary = customer_summary(conn, "ACME-001")
        assert summary.total_invoiced == 1250.00
        assert summary.outstanding == 250.00
