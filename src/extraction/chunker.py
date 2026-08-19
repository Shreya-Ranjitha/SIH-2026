"""Page-aware chunking so every extracted governance claim can cite a page number.

Chunks respect page boundaries: a chunk never silently merges text from two
pages without recording both page numbers, so downstream LLM extraction can
always report an honest page citation rather than guessing.
"""
from __future__ import annotations

from dataclasses import dataclass

from src.extraction.pdf_extract import DocumentText

DEFAULT_CHUNK_CHAR_LIMIT = 6000
DEFAULT_OVERLAP_CHARS = 400


@dataclass
class Chunk:
    chunk_index: int
    text: str
    page_start: int
    page_end: int


def chunk_document(doc: DocumentText, chunk_char_limit: int = DEFAULT_CHUNK_CHAR_LIMIT,
                    overlap_chars: int = DEFAULT_OVERLAP_CHARS) -> list[Chunk]:
    """Greedily pack whole pages into chunks up to chunk_char_limit characters.

    A page larger than chunk_char_limit becomes its own oversized chunk
    rather than being split mid-sentence (keeps clause citations intact).
    """
    chunks: list[Chunk] = []
    current_pages: list[tuple[int, str]] = []
    current_len = 0

    def flush():
        nonlocal current_pages, current_len
        if not current_pages:
            return
        text = "\n\n".join(f"[Page {p}]\n{t}" for p, t in current_pages)
        chunks.append(
            Chunk(
                chunk_index=len(chunks),
                text=text,
                page_start=current_pages[0][0],
                page_end=current_pages[-1][0],
            )
        )
        current_pages = []
        current_len = 0

    for page in doc.pages:
        page_text = page.text or ""
        if current_len + len(page_text) > chunk_char_limit and current_pages:
            flush()
            # carry a small overlap from the previous page's tail for context continuity
            if overlap_chars and chunks:
                prev_tail = chunks[-1].text[-overlap_chars:]
                current_pages = [(chunks[-1].page_end, prev_tail)]
                current_len = len(prev_tail)
        current_pages.append((page.page_number, page_text))
        current_len += len(page_text)

    flush()
    return chunks
