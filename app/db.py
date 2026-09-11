"""
Postgres persistence for invoice triage.

Two functions, raw SQL, no ORM — for two queries an ORM is more
machinery than the problem needs. Mirrors the shape of the
in-memory _SEEN_INVOICES set it replaces.
"""
import os
import psycopg2

def _connect():
    return psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=os.environ.get("POSTGRES_PORT", "5432"),
        dbname=os.environ.get("POSTGRES_DB", "invoice_triage"),
        user=os.environ.get("POSTGRES_USER", "triage"),
        password=os.environ.get("POSTGRES_PASSWORD", "triage_dev_pw"),
    )


def is_duplicate(vendor_name: str, invoice_number: str) -> bool:
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM invoices WHERE vendor_name = %s AND invoice_number = %s",
            (vendor_name, invoice_number),
        )
        return cur.fetchone() is not None


def record_invoice(vendor_name: str, invoice_number: str, total: float, status: str) -> None:
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO invoices (vendor_name, invoice_number, total, status)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (vendor_name, invoice_number) DO NOTHING
            """,
            (vendor_name, invoice_number, total, status),
        )
        conn.commit()
