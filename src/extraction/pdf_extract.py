"""Stage 3 — Tender document text extraction.

Primary path: PyMuPDF (fast, handles most digitally-generated tender PDFs).
Fallback: pdfplumber (better table handling for some government templates).
If both yield near-empty text, the caller should fall back to OCR
(see ocr_fallback.py) — this usually means the PDF is a scanned image.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

MIN_CHARS_PER_PAGE_BEFORE_OCR = 20  # below this average, assume scanned/needs OCR


@dataclass
class PageText:
    page_number: int  # 1-indexed, matches what a human would cite as "Page 47"
    text: str


@dataclass
class DocumentText:
    source_path: str
    pages: list[PageText]
    extraction_method: str  # "pymupdf" | "pdfplumber" | "ocr"

    @property
    def full_text(self) -> str:
        return "\n\n".join(f"[Page {p.page_number}]\n{p.text}" for p in self.pages)

    @property
    def avg_chars_per_page(self) -> float:
        if not self.pages:
            return 0.0
        return sum(len(p.text) for p in self.pages) / len(self.pages)


def extract_with_pymupdf(pdf_path: Path) -> DocumentText:
    import fitz  # PyMuPDF

    pages = []
    with fitz.open(pdf_path) as doc:
        for i, page in enumerate(doc, start=1):
            pages.append(PageText(page_number=i, text=page.get_text("text") or ""))
    return DocumentText(source_path=str(pdf_path), pages=pages, extraction_method="pymupdf")


def extract_with_pdfplumber(pdf_path: Path) -> DocumentText:
    import pdfplumber

    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            pages.append(PageText(page_number=i, text=page.extract_text() or ""))
    return DocumentText(source_path=str(pdf_path), pages=pages, extraction_method="pdfplumber")


def extract_text(pdf_path: Path) -> DocumentText:
    """Try PyMuPDF first, fall back to pdfplumber if it yields too little text.

    Caller (pipeline.py) is responsible for triggering OCR if this still
    returns near-empty pages (a scanned tender document).
    """
    try:
        result = extract_with_pymupdf(pdf_path)
        if result.avg_chars_per_page >= MIN_CHARS_PER_PAGE_BEFORE_OCR:
            return result
        logger.info("%s: PyMuPDF yielded low text density, trying pdfplumber", pdf_path.name)
    except Exception as exc:  # noqa: BLE001 - log and fall through to next strategy
        logger.warning("PyMuPDF extraction failed for %s: %s", pdf_path.name, exc)

    try:
        result = extract_with_pdfplumber(pdf_path)
        if result.avg_chars_per_page >= MIN_CHARS_PER_PAGE_BEFORE_OCR:
            return result
        logger.info("%s: pdfplumber also yielded low text density, needs OCR", pdf_path.name)
        return result  # still return it; pipeline decides whether to OCR
    except Exception as exc:  # noqa: BLE001
        logger.error("pdfplumber extraction also failed for %s: %s", pdf_path.name, exc)
        return DocumentText(source_path=str(pdf_path), pages=[], extraction_method="failed")
