"""OCR fallback for scanned tender PDFs.

Triggered by pipeline.py when pdf_extract.extract_text() returns a
DocumentText with avg_chars_per_page below the threshold, which usually
means the tender document is a scanned image (very common for older
Indian government tender notices published as photocopied PDFs).

Requires system packages: tesseract-ocr, poppler-utils.
"""
from __future__ import annotations

import logging
from pathlib import Path

from src.extraction.pdf_extract import DocumentText, PageText

logger = logging.getLogger(__name__)


def extract_with_ocr(pdf_path: Path, dpi: int = 300, lang: str = "eng") -> DocumentText:
    """Rasterize each page and run Tesseract OCR over it.

    `lang` defaults to English; pass "eng+hin" (or another combination) for
    tenders published bilingually, provided the corresponding tesseract
    language pack is installed.
    """
    from pdf2image import convert_from_path
    import pytesseract

    pages = []
    images = convert_from_path(str(pdf_path), dpi=dpi)
    for i, image in enumerate(images, start=1):
        try:
            text = pytesseract.image_to_string(image, lang=lang)
        except Exception as exc:  # noqa: BLE001
            logger.warning("OCR failed on page %d of %s: %s", i, pdf_path.name, exc)
            text = ""
        pages.append(PageText(page_number=i, text=text))

    return DocumentText(source_path=str(pdf_path), pages=pages, extraction_method="ocr")
