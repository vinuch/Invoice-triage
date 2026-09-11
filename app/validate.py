"""
Deterministic validation layer.

Core principle: AI extracts, code decides. Never let the model's confidence
score alone gate a financial decision — verify what can be verified.
"""
from app.models import Extraction, Flag, TriageResult
from app import db

AUTO_APPROVE_THRESHOLD = 5000.00
CONFIDENCE_FLOOR = 0.90
MATH_TOLERANCE = 0.01  # cents-level rounding slack

def verify_math(extraction: Extraction) -> Flag | None:
    f = extraction.financials
    expected_total = round(f.subtotal + f.tax_amount, 2)
    if abs(expected_total - f.total) > MATH_TOLERANCE:
        return Flag(
            type="math_mismatch",
            severity="high",
            message=f"Subtotal ({f.subtotal}) + tax ({f.tax_amount}) = {expected_total}, "
                    f"but stated total is {f.total}.",
        )
    return None


def check_duplicate(extraction: Extraction) -> Flag | None:
    vendor = extraction.vendor.name.strip().lower()
    number = extraction.invoice.number.strip()
    if db.is_duplicate(vendor, number):
        return Flag(
            type="duplicate",
            severity="high",
            message=f"Invoice {extraction.invoice.number} from {extraction.vendor.name} "
                    f"has already been processed.",
        )
    db.record_invoice(vendor, number, extraction.financials.total, "seen")
    return None


def check_confidence(extraction: Extraction) -> Flag | None:
    if extraction.overall_confidence < CONFIDENCE_FLOOR:
        return Flag(
            type="low_confidence",
            severity="medium",
            message=f"Overall extraction confidence ({extraction.overall_confidence:.2f}) "
                    f"is below the {CONFIDENCE_FLOOR} floor.",
        )
    return None


def check_missing_po(extraction: Extraction) -> Flag | None:
    if extraction.invoice.po_number is None and extraction.financials.total > 1000:
        return Flag(
            type="missing_po",
            severity="medium",
            message="No PO number found on an invoice over $1,000.",
        )
    return None


def check_high_value(extraction: Extraction) -> Flag | None:
    if extraction.financials.total > AUTO_APPROVE_THRESHOLD:
        return Flag(
            type="high_value",
            severity="medium",
            message=f"Invoice total (${extraction.financials.total:,.2f}) exceeds "
                    f"auto-approval threshold of ${AUTO_APPROVE_THRESHOLD:,.2f}.",
        )
    return None


def triage(extraction: Extraction) -> TriageResult:
    checks = [
        verify_math(extraction),
        check_duplicate(extraction),
        check_confidence(extraction),
        check_missing_po(extraction),
        check_high_value(extraction),
    ]
    flags = [f for f in checks if f is not None]

    if any(f.severity == "high" for f in flags):
        status = "flagged"
    elif flags:
        status = "needs_review"
    else:
        status = "approved"

    summary = _build_summary(extraction, flags, status)
    return TriageResult(extraction=extraction, flags=flags, status=status, summary=summary)


def _build_summary(extraction: Extraction, flags: list[Flag], status: str) -> str:
    base = (
        f"{extraction.vendor.name} issued invoice {extraction.invoice.number} for "
        f"{extraction.financials.currency} {extraction.financials.total:,.2f}"
    )
    if extraction.invoice.due_date:
        base += f", due {extraction.invoice.due_date}"
    base += "."
    if not flags:
        base += " No issues detected."
    else:
        reasons = "; ".join(f.message for f in flags)
        base += f" Status: {status}. {reasons}"
    return base
