"""
Normalize incoming invoice files to PNG before they hit extraction.

Extraction expects a PNG. Real-world invoices show up as PDFs as
often as images, so this is the one place that difference gets
resolved — everything downstream can assume a clean PNG path.
"""
import os
from pdf2image import convert_from_path

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}


def normalize_to_png(file_path: str) -> str:
    """
    Given a path to an uploaded file (image or PDF), return a path
    to a PNG on disk. Images pass through untouched. PDFs get their
    first page rendered to PNG at 200 DPI.
    """
    ext = os.path.splitext(file_path)[1].lower()

    if ext in IMAGE_EXTENSIONS:
        return file_path

    if ext == ".pdf":
        pages = convert_from_path(file_path, dpi=200, first_page=1, last_page=1)
        png_path = os.path.splitext(file_path)[0] + ".png"
        pages[0].save(png_path, "PNG")
        return png_path

    raise ValueError(f"Unsupported file type: {ext}")
