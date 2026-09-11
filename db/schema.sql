CREATE TABLE IF NOT EXISTS invoices (
    id SERIAL PRIMARY KEY,
    vendor_name TEXT NOT NULL,
    invoice_number TEXT NOT NULL,
    total NUMERIC(12, 2) NOT NULL,
    status TEXT NOT NULL,
    processed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (vendor_name, invoice_number)
);
