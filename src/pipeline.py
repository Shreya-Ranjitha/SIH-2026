"""Orchestrates the full pipeline described in the pitch:

Millions of Tender Records
      -> Stage 1: AI Tender Discovery (keyword filter + LLM verification)
      -> Stage 2: Curated Deep-Dive (select top-N priority candidates)
      -> Stage 3: Tender Document Extraction (PDF/OCR -> chunks)
      -> Governance Evidence Extraction (4 dimensions, LLM structured output)
      -> Impact Classification (deterministic)
      -> Evidence Database (SQLite)
"""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

import config
from src.discovery.filter import filter_candidates, load_tenders, save_candidates
from src.discovery.verify import verify_candidate
from src.extraction.chunker import chunk_document
from src.extraction.pdf_extract import extract_text
from src.extraction.ocr_fallback import extract_with_ocr
from src.governance.extractor import extract_all_dimensions
from src.governance.impact_classifier import classify_impact
from src.storage import db
from src.storage.models import ConfirmedAITender, TenderCandidate

logger = logging.getLogger(__name__)


def run_discovery(raw_parquet: Path = config.RAW_TENDERS_PARQUET,
                   out_parquet: Path = config.CANDIDATES_PARQUET) -> pd.DataFrame:
    """Stage 1: load raw tenders, keyword-filter, save candidates."""
    df = load_tenders(raw_parquet)
    candidates = filter_candidates(df)
    save_candidates(candidates, out_parquet)
    return candidates


def run_verification(candidates_df: pd.DataFrame, client, model: str = config.CLAUDE_MODEL) -> list[ConfirmedAITender]:
    """Stage 1 (second pass): LLM-verify each candidate, return confirmed AI tenders."""
    confirmed = []
    for _, row in candidates_df.iterrows():
        candidate = TenderCandidate(
            tender_id=str(row.get("tender_id")),
            organisation=row.get("organisation", ""),
            state=row.get("state"),
            title=row.get("title", ""),
            tender_description=row.get("tender_description", ""),
            tender_type=row.get("tender_type"),
            tender_date=row.get("date"),
            contract_value=row.get("contract_value"),
            detail_url=row.get("detail_url"),
            tender_document_url=row.get("tender_document_url"),
            matched_ai_types=row.get("matched_ai_types", []),
            keyword_hit_count=row.get("keyword_hit_count", 0),
        )
        result = verify_candidate(candidate, client=client, model=model)
        if result.is_ai_confirmed:
            confirmed.append(
                ConfirmedAITender(
                    tender_id=result.tender_id,
                    organisation=candidate.organisation,
                    state=candidate.state,
                    title=candidate.title,
                    ai_type=result.ai_type,
                    confidence=result.confidence,
                    verification_reasoning=result.reasoning,
                )
            )
    logger.info("Verification: %d / %d candidates confirmed as genuine AI tenders",
                len(confirmed), len(candidates_df))
    return confirmed


def select_priority_tenders(confirmed: list[ConfirmedAITender], top_n: int = config.DEEP_DIVE_TOP_N) -> list[ConfirmedAITender]:
    """Stage 2: pick the curated deep-dive set, prioritizing high-impact AI types."""
    priority_types = {
        "Facial Recognition", "Biometric Identification", "Computer Vision",
        "Generative AI / LLM", "Conversational AI", "Predictive Analytics",
    }
    ranked = sorted(confirmed, key=lambda t: t.ai_type not in priority_types)
    selected = ranked[:top_n]
    for tender in selected:
        tender.is_priority = True
    return selected


def run_document_pipeline(pdf_path: Path, tender_id: str, client, model: str = config.CLAUDE_MODEL):
    """Stage 3 + governance extraction for one tender document."""
    doc = extract_text(pdf_path)
    if doc.avg_chars_per_page < 20:
        logger.info("%s: falling back to OCR (low text density from direct extraction)", pdf_path.name)
        doc = extract_with_ocr(pdf_path)

    chunks = chunk_document(doc)
    if not chunks:
        logger.warning("%s: no extractable text even after OCR fallback", pdf_path.name)
        return {}

    findings = extract_all_dimensions(client, model, tender_id, chunks, source_document=pdf_path.name)
    return findings


def persist_tender(tender: ConfirmedAITender, findings: dict, description: str = "",
                    db_path: Path = config.SQLITE_DB_PATH) -> None:
    impact_level, impact_reasoning = classify_impact(tender.ai_type, tender.title, description)
    db.init_db(db_path)
    db.upsert_confirmed_tender(db_path, tender, impact_level=impact_level, impact_reasoning=impact_reasoning)
    for finding in findings.values():
        db.save_finding(db_path, finding)
    logger.info("Persisted tender %s (%s) with %d findings", tender.tender_id, impact_level.value, len(findings))
