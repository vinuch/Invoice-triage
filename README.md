# Invoice Triage

A minimal, real invoice extraction + validation pipeline. No OCR, no templates —
a vision-capable LLM reads the invoice image directly and returns structured JSON.
A deterministic validation layer (not the LLM) decides whether it's safe to auto-approve.

This is the Build 1 v0 core: extraction + validation. Dashboard, Gmail ingestion,
and Docker deployment are follow-on milestones, not required to run this.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# edit .env and add your ANTHROPIC_API_KEY (or OPENAI_API_KEY)
```

## Run on a real invoice

```bash
python -m app.run path/to/invoice.png
# or force a provider:
python -m app.run path/to/invoice.png openai
```

Outputs structured JSON + a human-readable summary + a status (`approved` /
`needs_review` / `flagged`).

## Run the tests (no API key needed)

```bash
python tests/test_validate.py
```

This proves the validation rules work in isolation — math verification,
duplicate detection, high-value routing, missing-PO flagging — without
spending a single API call.

## How it works

```
image → extract.py (VLM call, structured JSON out)
      → validate.py (deterministic rules: math, duplicates, thresholds)
      → TriageResult (status + flags + summary)
```

The core principle: the LLM extracts, code decides. Confidence scores inform
review routing, but financial correctness (does subtotal + tax = total?) is
verified in plain Python, not trusted from the model's output.

## What's next (later milestones)

- Gmail/Drive ingestion
- Review queue + dashboard
- Docker deployment
- Benchmark suite against a labeled invoice set

## License

MIT
