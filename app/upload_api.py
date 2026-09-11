"""
Upload API — accepts a file, normalizes it, runs the same
extract-validate pipeline from lessons 1 and 2, returns JSON.
No new logic. This is plumbing.

    uvicorn app.upload_api:app --reload
"""
import os
import tempfile

from fastapi import FastAPI, UploadFile, File, HTTPException
from dotenv import load_dotenv

load_dotenv()

from app.normalize import normalize_to_png
from app.extract import extract_invoice
from app.validate import triage

app = FastAPI()

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".pdf"}


@app.post("/triage")
async def triage_invoice(file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name

        png_path = normalize_to_png(tmp_path)
        extraction = extract_invoice(png_path, provider="openrouter")
        result = triage(extraction)
        return result.model_dump()

    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)
        if tmp_path:
            png_path_guess = os.path.splitext(tmp_path)[0] + ".png"
            if os.path.exists(png_path_guess) and png_path_guess != tmp_path:
                os.remove(png_path_guess)
