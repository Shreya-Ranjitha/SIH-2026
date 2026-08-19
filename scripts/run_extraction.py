#!/usr/bin/env python
"""CLI entrypoint for Stage 2 (curated deep-dive) + Stage 3 (document extraction)
+ governance evidence extraction + impact classification + persistence.

Usage:
    python scripts/run_extraction.py --top-n 20 --priority-only
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import requests

import config
from src.pipeline import (
    persist_tender,
    run_document_pipeline,
    run_verification,
    select_priority_tenders,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def download_document(url: str, dest_dir: Path) -> Path | None:
    dest_dir.mkdir(parents=True, exist_ok=True)
    filename = url.split("/")[-1] or "document.pdf"
    dest = dest_dir / filename
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        dest.write_bytes(resp.content)
        return dest
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not download %s: %s", url, exc)
        return None


def main():
    parser = argparse.ArgumentParser(description="Stage 2/3: curated deep-dive + document extraction")
    parser.add_argument("--top-n", type=int, default=config.DEEP_DIVE_TOP_N)
    parser.add_argument("--priority-only", action="store_true",
                         help="Only process the top-N priority AI types (facial recognition, GenAI, etc.)")
    args = parser.parse_args()

    if not config.ANTHROPIC_API_KEY:
        raise SystemExit(
            "ANTHROPIC_API_KEY is not set. Copy .env.example to .env and fill it in, "
            "or run scripts/seed_demo_data.py for an offline demo instead."
        )

    import anthropic

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    if not config.CANDIDATES_PARQUET.exists():
        raise SystemExit("No candidates found. Run scripts/run_discovery.py first.")

    candidates_df = pd.read_parquet(config.CANDIDATES_PARQUET)
    logger.info("Loaded %d candidates for verification", len(candidates_df))

    confirmed = run_verification(candidates_df, client=client)
    selected = select_priority_tenders(confirmed, top_n=args.top_n) if args.priority_only else confirmed[: args.top_n]
    logger.info("Selected %d tenders for deep-dive document extraction", len(selected))

    for tender in selected:
        row = candidates_df[candidates_df["tender_id"] == tender.tender_id]
        doc_url = row["tender_document_url"].iloc[0] if not row.empty else None
        description = row["tender_description"].iloc[0] if not row.empty else ""
        if not doc_url:
            logger.warning("No document URL for %s, skipping document extraction", tender.tender_id)
            persist_tender(tender, findings={}, description=description)
            continue

        pdf_path = download_document(doc_url, config.DOCUMENTS_DIR)
        if pdf_path is None:
            persist_tender(tender, findings={}, description=description)
            continue

        findings = run_document_pipeline(pdf_path, tender.tender_id, client=client)
        persist_tender(tender, findings=findings, description=description)

    print(f"\nDone. {len(selected)} tenders processed into {config.SQLITE_DB_PATH}")
    print("Launch the dashboard: streamlit run app/streamlit_app.py")


if __name__ == "__main__":
    main()
