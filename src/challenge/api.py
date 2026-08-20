"""HTTP API for the settlements service.

Consumed by the internal customer page that the account team uses.
"""

from __future__ import annotations

from dataclasses import asdict

from fastapi import FastAPI, HTTPException

from challenge import ledger
from challenge.store import connect

app = FastAPI(title="Settlements", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/customers")
def list_customers() -> list[dict]:
    conn = connect()
    try:
        rows = conn.execute("SELECT * FROM customers ORDER BY customer_id").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@app.get("/customers/{customer_id}/summary")
def customer_summary(customer_id: str) -> dict:
    conn = connect()
    try:
        summary = ledger.customer_summary(conn, customer_id)
        if summary is None:
            raise HTTPException(status_code=404, detail=f"Unknown customer {customer_id}")
        payload = asdict(summary)
        payload["invoices"] = [
            {**asdict(line), "outstanding": line.outstanding} for line in summary.invoices
        ]
        return payload
    finally:
        conn.close()


@app.get("/payments/unmatched")
def unmatched_payments(customer_id: str | None = None) -> list[dict]:
    conn = connect()
    try:
        return [dict(r) for r in ledger.unmatched_payments(conn, customer_id)]
    finally:
        conn.close()
