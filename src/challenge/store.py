"""SQLite persistence for the settlements service.

Three tables:

  customers  reference data, loaded once
  invoices   what we have billed, plus how much of it has been paid
  payments   what the bank told us arrived

The database file lives at the project root and is disposable: `make reset`
drops it and reloads the reference data from data/.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = PROJECT_ROOT / "settlements.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS customers (
    customer_id     TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    country         TEXT,
    currency        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS invoices (
    invoice_id      TEXT PRIMARY KEY,
    customer_id     TEXT NOT NULL,
    issue_date      TEXT NOT NULL,
    due_date        TEXT NOT NULL,
    total_amount    REAL NOT NULL,
    currency        TEXT NOT NULL,
    amount_paid     REAL NOT NULL DEFAULT 0,
    status          TEXT NOT NULL DEFAULT 'open'
);

CREATE TABLE IF NOT EXISTS payments (
    bank_reference  TEXT PRIMARY KEY,
    customer_id     TEXT NOT NULL,
    value_date      TEXT NOT NULL,
    amount          REAL NOT NULL,
    currency        TEXT NOT NULL,
    remittance_info TEXT,
    source_file     TEXT NOT NULL,
    imported_at     TEXT NOT NULL,
    matched_at      TEXT
);
"""


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    """Open a connection with row access by column name."""
    conn = sqlite3.connect(db_path or DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def drop_all(db_path: Path | None = None) -> None:
    """Delete the database file so the next connect() starts clean."""
    path = db_path or DB_PATH
    if path.exists():
        path.unlink()
