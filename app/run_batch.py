"""
Batch demo runner. Processes all sample invoices in one process so
duplicate detection works correctly (in-memory _SEEN_INVOICES persists
across the batch, unlike separate CLI calls).

    python -m app.run_batch
    python -m app.run_batch gemini

This IS the recording take for the "proof" section of the video.
"""
import json
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from app.extract import extract_invoice
from app.validate import triage

SAMPLE_DIR = Path(__file__).parent.parent / "sample_data"

# Order matters for the demo narrative: clean -> math error -> missing PO
# -> high value -> duplicate (of the first one).
INVOICE_ORDER = [
    "invoice_01_clean.png",
    "invoice_02_math_error.png",
    "invoice_03_missing_po.png",
    "invoice_04_high_value.png",
    "invoice_05_duplicate_of_01.png",
]


def main():
    provider = sys.argv[1] if len(sys.argv) > 1 else "anthropic"

    results = []
    for filename in INVOICE_ORDER:
        image_path = SAMPLE_DIR / filename
        if not image_path.exists():
            print(f"Skipping {filename} (not found)")
            continue

        print(f"\n{'=' * 60}")
        print(f"Processing: {filename}")
        print(f"{'=' * 60}")

        extraction = extract_invoice(str(image_path), provider=provider)
        result = triage(extraction)
        results.append((filename, result))

        print(f"Vendor:  {extraction.vendor.name}")
        print(f"Invoice: {extraction.invoice.number}")
        print(f"Total:   {extraction.financials.currency} {extraction.financials.total:,.2f}")
        print(f"Status:  {result.status.upper()}")
        if result.flags:
            for flag in result.flags:
                print(f"  [{flag.severity.upper()}] {flag.type}: {flag.message}")

    print(f"\n{'=' * 60}")
    print("BATCH SUMMARY")
    print(f"{'=' * 60}")
    for filename, result in results:
        print(f"{filename:40s} -> {result.status.upper()}")


if __name__ == "__main__":
    main()