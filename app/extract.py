"""
Invoice extraction via vision-capable LLM.

Design choice: native image -> structured JSON, no OCR middle step.
Swap PROVIDER to point at whichever vision model you have API access to.
"""
import base64
import json
import os
from app.models import Extraction

EXTRACTION_PROMPT = """You are an invoice data extraction system. Look at the invoice image
and extract the following fields as strict JSON matching this schema exactly:

{
  "document_id": "<generate a short unique id>",
  "vendor": {"name": "...", "address": "...", "tax_id": "...", "confidence": 0.0-1.0},
  "invoice": {"number": "...", "date": "YYYY-MM-DD", "due_date": "YYYY-MM-DD", "terms": "...", "po_number": "... or null", "confidence": 0.0-1.0},
  "financials": {"currency": "...", "subtotal": 0.0, "tax_rate": 0.0, "tax_amount": 0.0, "total": 0.0, "confidence": 0.0-1.0},
  "line_items": [{"description": "...", "quantity": 1, "unit_price": 0.0, "total": 0.0}],
  "category": "...",
  "overall_confidence": 0.0-1.0
}

Rules:
- If a field is not visible or not present, use null (never invent a value).
- confidence reflects how certain you are the extracted value is correct, not whether the field exists.
- Respond with ONLY the JSON object. No markdown, no commentary.
"""


def _encode_image(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


# def extract_invoice(image_path: str, provider: str = "anthropic") -> Extraction:
#     """
#     Extract structured invoice data from an image file.
#     provider: "anthropic" | "openai" | "gemini"
#     Requires the relevant API key in env (ANTHROPIC_API_KEY / OPENAI_API_KEY / GOOGLE_API_KEY).
#     """
#     image_b64 = _encode_image(image_path)
#     media_type = "image/png" if image_path.lower().endswith("png") else "image/jpeg"

#     if provider == "anthropic":
#         raw_json = _call_anthropic(image_b64, media_type)
#     elif provider == "openai":
#         raw_json = _call_openai(image_b64, media_type)
#     else:
#         raise ValueError(f"Unsupported provider: {provider}")

#     data = json.loads(raw_json)
#     return Extraction(**data)

def _call_gemini(image_b64: str, media_type: str) -> str:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            types.Part.from_bytes(data=base64.b64decode(image_b64), mime_type=media_type),
            EXTRACTION_PROMPT,
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
        ),
    )
    return response.text

def extract_invoice(image_path: str, provider: str = "anthropic") -> Extraction:
    """
    Extract structured invoice data from an image file.
    provider: "anthropic" | "openai" | "gemini"
    Requires the relevant API key in env (ANTHROPIC_API_KEY / OPENAI_API_KEY / GOOGLE_API_KEY).
    """
    image_b64 = _encode_image(image_path)
    media_type = "image/png" if image_path.lower().endswith("png") else "image/jpeg"

    # Auto-fallback: if caller didn't explicitly request a provider and the
    # default has no key configured, fall back to Gemini (free tier, dev use)
    if provider == "anthropic" and not os.environ.get("ANTHROPIC_API_KEY"):
        if os.environ.get("GOOGLE_API_KEY"):
            provider = "gemini"

    if provider == "anthropic":
        raw_json = _call_anthropic(image_b64, media_type)
    elif provider == "openai":
        raw_json = _call_openai(image_b64, media_type)
    elif provider == "gemini":
        raw_json = _call_gemini(image_b64, media_type)
    else:
        raise ValueError(f"Unsupported provider: {provider}")

    data = json.loads(raw_json)
    return Extraction(**data)

def _call_anthropic(image_b64: str, media_type: str) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": image_b64}},
                    {"type": "text", "text": EXTRACTION_PROMPT},
                ],
            }
        ],
    )
    return response.content[0].text


def _call_openai(image_b64: str, media_type: str) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    response = client.chat.completions.create(
        model="gpt-4o",
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": EXTRACTION_PROMPT},
                    {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{image_b64}"}},
                ],
            }
        ],
    )
    return response.choices[0].message.content
