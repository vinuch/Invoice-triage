"""
Synthetic invoice generator.

Generates realistic-looking invoices as HTML, rendered to PNG via wkhtmltoimage.
Covers the edge cases the validation engine is designed to catch, so you have
a demo set that actually exercises every rule in validate.py.

Run: python3 sample_data/generate_invoices.py
"""
import json
import os
import subprocess

OUT_DIR = os.path.dirname(__file__)

INVOICE_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
<style>
  body {{ font-family: 'Helvetica Neue', Arial, sans-serif; margin: 0; padding: 50px; color: #1a1a1a; }}
  .header {{ display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 3px solid #2c3e50; padding-bottom: 20px; margin-bottom: 30px; }}
  .company {{ font-size: 26px; font-weight: 700; color: #2c3e50; }}
  .invoice-title {{ text-align: right; }}
  .invoice-title h1 {{ font-size: 32px; color: #7f8c8d; margin: 0; letter-spacing: 2px; }}
  .invoice-title p {{ margin: 4px 0; color: #555; }}
  .meta {{ display: flex; justify-content: space-between; margin-bottom: 30px; }}
  .meta div {{ font-size: 14px; line-height: 1.6; }}
  .meta strong {{ color: #2c3e50; }}
  table {{ width: 100%; border-collapse: collapse; margin-bottom: 30px; }}
  th {{ background: #2c3e50; color: white; text-align: left; padding: 10px 12px; font-size: 13px; }}
  td {{ padding: 10px 12px; border-bottom: 1px solid #eee; font-size: 14px; }}
  .totals {{ width: 300px; margin-left: auto; }}
  .totals div {{ display: flex; justify-content: space-between; padding: 6px 0; font-size: 14px; }}
  .totals .grand {{ font-weight: 700; font-size: 18px; border-top: 2px solid #2c3e50; padding-top: 10px; margin-top: 6px; }}
  .footer {{ margin-top: 40px; font-size: 12px; color: #888; border-top: 1px solid #eee; padding-top: 15px; }}
</style>
</head>
<body>
  <div class="header">
    <div class="company">{vendor_name}</div>
    <div class="invoice-title">
      <h1>INVOICE</h1>
      <p>{invoice_number}</p>
    </div>
  </div>
  <div class="meta">
    <div>
      <strong>Bill To:</strong><br>
      Northwind Trading Co.<br>
      1180 Market St, Suite 400<br>
      San Francisco, CA 94103
    </div>
    <div>
      <strong>Invoice Date:</strong> {invoice_date}<br>
      <strong>Due Date:</strong> {due_date}<br>
      <strong>Terms:</strong> {terms}<br>
      <strong>PO Number:</strong> {po_number}
    </div>
  </div>
  <table>
    <tr><th>Description</th><th>Qty</th><th>Unit Price</th><th>Total</th></tr>
    {line_items_html}
  </table>
  <div class="totals">
    <div><span>Subtotal</span><span>${subtotal:,.2f}</span></div>
    <div><span>Tax ({tax_rate_pct}%)</span><span>${tax_amount:,.2f}</span></div>
    <div class="grand"><span>Total Due</span><span>${total:,.2f}</span></div>
  </div>
  <div class="footer">
    {vendor_name} &middot; Tax ID: {tax_id} &middot; Thank you for your business.
  </div>
</body>
</html>
"""

LINE_ITEM_ROW = "<tr><td>{description}</td><td>{quantity}</td><td>${unit_price:,.2f}</td><td>${total:,.2f}</td></tr>"


def render_invoice(name: str, vendor_name: str, invoice_number: str, invoice_date: str,
                    due_date: str, terms: str, po_number: str, line_items: list[dict],
                    tax_rate: float, displayed_total: float | None = None, tax_id: str = "94-1234567"):
    subtotal = sum(li["total"] for li in line_items)
    tax_amount = round(subtotal * tax_rate, 2)
    total = displayed_total if displayed_total is not None else round(subtotal + tax_amount, 2)

    rows_html = "\n".join(LINE_ITEM_ROW.format(**li) for li in line_items)

    html = INVOICE_TEMPLATE.format(
        vendor_name=vendor_name,
        invoice_number=invoice_number,
        invoice_date=invoice_date,
        due_date=due_date,
        terms=terms,
        po_number=po_number or "\u2014",
        line_items_html=rows_html,
        subtotal=subtotal,
        tax_rate_pct=round(tax_rate * 100, 1),
        tax_amount=tax_amount,
        total=total,
        tax_id=tax_id,
    )

    html_path = os.path.join(OUT_DIR, f"{name}.html")
    png_path = os.path.join(OUT_DIR, f"{name}.png")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(f'<meta charset="UTF-8">\n{html}')

    subprocess.run(
        ["wkhtmltoimage", "--width", "900", "--quality", "92", html_path, png_path],
        check=True, capture_output=True,
    )
    os.remove(html_path)

    # Ground truth for benchmark/eval use
    ground_truth = {
        "document_id": name,
        "vendor_name": vendor_name,
        "invoice_number": invoice_number,
        "invoice_date": invoice_date,
        "due_date": due_date,
        "terms": terms,
        "po_number": po_number,
        "subtotal": subtotal,
        "tax_rate": tax_rate,
        "tax_amount": tax_amount,
        "total": total,
        "line_items": line_items,
    }
    return ground_truth


def main():
    invoices = []

    # 1. Clean invoice — should auto-approve
    invoices.append(render_invoice(
        name="invoice_01_clean",
        vendor_name="Acme Consulting Partners LLC",
        invoice_number="INV-4521",
        invoice_date="2026-07-15",
        due_date="2026-08-14",
        terms="Net 30",
        po_number="PO-2026-0892",
        line_items=[{"description": "Strategic planning services \u2014 July 2026", "quantity": 1, "unit_price": 4200.00, "total": 4200.00}],
        tax_rate=0.0,
    ))

    # 2. Math mismatch — the "$100,000 typo" case
    invoices.append(render_invoice(
        name="invoice_02_math_error",
        vendor_name="TechSupplyCo Inc.",
        invoice_number="7783",
        invoice_date="2026-07-28",
        due_date="2026-08-27",
        terms="Net 30",
        po_number="PO-2026-1140",
        line_items=[{"description": "Server rack \u2014 42U", "quantity": 2, "unit_price": 500.00, "total": 1000.00}],
        tax_rate=0.08,
        displayed_total=100000.00,  # deliberately wrong — stated total doesn't match subtotal+tax
    ))

    # 3. Missing PO on a high-value invoice
    invoices.append(render_invoice(
        name="invoice_03_missing_po",
        vendor_name="Meridian Office Supplies",
        invoice_number="MOS-88213",
        invoice_date="2026-07-20",
        due_date="2026-08-19",
        terms="Net 30",
        po_number=None,
        line_items=[
            {"description": "Standing desks (6 units)", "quantity": 6, "unit_price": 380.00, "total": 2280.00},
            {"description": "Ergonomic chairs (6 units)", "quantity": 6, "unit_price": 310.00, "total": 1860.00},
        ],
        tax_rate=0.0825,
    ))

    # 4. High-value, exceeds auto-approve threshold
    invoices.append(render_invoice(
        name="invoice_04_high_value",
        vendor_name="Precision Manufacturing Co.",
        invoice_number="PMC-2026-3391",
        invoice_date="2026-07-10",
        due_date="2026-08-09",
        terms="Net 30",
        po_number="PO-2026-0771",
        line_items=[{"description": "CNC machining \u2014 batch run 400 units", "quantity": 400, "unit_price": 19.75, "total": 7900.00}],
        tax_rate=0.0,
    ))

    # 5. Exact duplicate of invoice 1 (same vendor + number) — for duplicate-detection demo
    invoices.append(render_invoice(
        name="invoice_05_duplicate_of_01",
        vendor_name="Acme Consulting Partners LLC",
        invoice_number="INV-4521",
        invoice_date="2026-07-15",
        due_date="2026-08-14",
        terms="Net 30",
        po_number="PO-2026-0892",
        line_items=[{"description": "Strategic planning services \u2014 July 2026", "quantity": 1, "unit_price": 4200.00, "total": 4200.00}],
        tax_rate=0.0,
    ))

    with open(os.path.join(OUT_DIR, "ground_truth.json"), "w") as f:
        json.dump(invoices, f, indent=2)

    print(f"Generated {len(invoices)} synthetic invoices in {OUT_DIR}/")
    for inv in invoices:
        print(f"  - {inv['document_id']}.png")


if __name__ == "__main__":
    main()
