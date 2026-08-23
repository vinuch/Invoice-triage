"""
Tests for the deterministic validation layer — no LLM calls, runs instantly.
This is what you'd screen-record for the 'validation catches an error' lesson.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.models import Extraction, VendorInfo, InvoiceDetails, Financials
from app.validate import triage, _SEEN_INVOICES


def make_extraction(**overrides) -> Extraction:
    base = dict(
        document_id="test_001",
        vendor=VendorInfo(name="Acme Consulting", confidence=0.97),
        invoice=InvoiceDetails(number="INV-001", due_date="2026-09-01", po_number="PO-123", confidence=0.98),
        financials=Financials(currency="USD", subtotal=1000.0, tax_rate=0.0, tax_amount=0.0, total=1000.0, confidence=0.98),
        overall_confidence=0.97,
    )
    base.update(overrides)
    return Extraction(**base)


def test_clean_invoice_approves():
    _SEEN_INVOICES.clear()
    result = triage(make_extraction())
    assert result.status == "approved"
    assert result.flags == []
    print("PASS: clean invoice auto-approves")


def test_math_mismatch_flagged():
    _SEEN_INVOICES.clear()
    bad = make_extraction(financials=Financials(
        currency="USD", subtotal=1000.0, tax_rate=0.0, tax_amount=0.0, total=100000.0, confidence=0.95
    ))
    result = triage(bad)
    assert result.status == "flagged"
    assert any(f.type == "math_mismatch" for f in result.flags)
    print("PASS: math mismatch caught (the $100,000 typo case)")


def test_duplicate_detected():
    _SEEN_INVOICES.clear()
    inv = make_extraction()
    triage(inv)  # first pass, seen now
    result = triage(inv)  # same invoice again
    assert result.status == "flagged"
    assert any(f.type == "duplicate" for f in result.flags)
    print("PASS: duplicate invoice caught on second submission")


def test_high_value_needs_review():
    _SEEN_INVOICES.clear()
    big = make_extraction(financials=Financials(
        currency="USD", subtotal=8000.0, tax_rate=0.0, tax_amount=0.0, total=8000.0, confidence=0.97
    ))
    result = triage(big)
    assert result.status == "needs_review"
    assert any(f.type == "high_value" for f in result.flags)
    print("PASS: high-value invoice routed to review, not auto-approved")


def test_missing_po_flagged():
    _SEEN_INVOICES.clear()
    no_po = make_extraction(invoice=InvoiceDetails(number="INV-002", due_date="2026-09-01", po_number=None, confidence=0.95))
    result = triage(no_po)
    assert any(f.type == "missing_po" for f in result.flags)
    print("PASS: missing PO on >$1000 invoice flagged")


if __name__ == "__main__":
    test_clean_invoice_approves()
    test_math_mismatch_flagged()
    test_duplicate_detected()
    test_high_value_needs_review()
    test_missing_po_flagged()
    print("\nAll validation tests passed.")
