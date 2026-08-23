"""
Minimal end-to-end runner. This IS the Sunday demo:

    python -m app.run sample_data/invoice_01.png

Prints structured JSON + human summary. No server, no Docker, no DB —
just the core pipeline: extract -> validate -> triage.
"""
import json
import sys
from app.extract import extract_invoice
from app.validate import triage

from dotenv import load_dotenv
load_dotenv()


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m app.run <path_to_invoice_image> [provider]")
        sys.exit(1)

    image_path = sys.argv[1]
    provider = sys.argv[2] if len(sys.argv) > 2 else "anthropic"

    print(f"Extracting {image_path} via {provider}...")
    extraction = extract_invoice(image_path, provider=provider)

    result = triage(extraction)

    print("\n--- Structured Output ---")
    print(json.dumps(result.model_dump(), indent=2))

    print("\n--- Summary ---")
    print(result.summary)
    print(f"\nStatus: {result.status.upper()}")


if __name__ == "__main__":
    main()
