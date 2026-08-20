"""Loading data into the settlements service.

Reference data (customers, invoices) is loaded once at reset time.

Payment files are the nightly export from the bank. The bank sends a rolling
window rather than only what is new, so the same transaction shows up in
several consecutive files. Import is therefore keyed on the bank reference:
a transaction we have already stored is skipped.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from sqlite3 import Connection

from challenge.store import DATA_DIR


@dataclass
class ImportResult:
    source_file: str
    rows_read: int
    inserted: int
    skipped: int

    def __str__(self) -> str:
        return (
            f"{self.source_file}: {self.rows_read} rows read, "
            f"{self.inserted} inserted, {self.skipped} already known"
        )


def _read_csv(path: Path) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_reference_data(conn: Connection, data_dir: Path | None = None) -> None:
    """Load customers and invoices from the CSV reference files."""
    data_dir = data_dir or DATA_DIR

    for row in _read_csv(data_dir / "customers.csv"):
        conn.execute(
            "INSERT OR REPLACE INTO customers (customer_id, name, country, currency) "
            "VALUES (?, ?, ?, ?)",
            (row["customer_id"], row["name"], row["country"], row["currency"]),
        )

    for row in _read_csv(data_dir / "invoices.csv"):
        conn.execute(
            "INSERT OR REPLACE INTO invoices "
            "(invoice_id, customer_id, issue_date, due_date, total_amount, currency) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                row["invoice_id"],
                row["customer_id"],
                row["issue_date"],
                row["due_date"],
                float(row["total_amount"]),
                row["currency"],
            ),
        )

    conn.commit()


def import_payments(conn: Connection, path: Path) -> ImportResult:
    """Import one nightly bank file. Transactions already stored are skipped."""
    rows = _read_csv(path)
    imported_at = datetime.now(timezone.utc).isoformat()
    inserted = 0

    for row in rows:
        cursor = conn.execute(
            "INSERT OR IGNORE INTO payments "
            "(bank_reference, customer_id, value_date, amount, currency, "
            " remittance_info, source_file, imported_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                row["bank_reference"],
                row["customer_id"],
                row["value_date"],
                float(row["amount"]),
                row["currency"],
                row["remittance_info"],
                path.name,
                imported_at,
            ),
        )
        inserted += cursor.rowcount

    conn.commit()
    return ImportResult(
        source_file=path.name,
        rows_read=len(rows),
        inserted=inserted,
        skipped=len(rows) - inserted,
    )
