"""Stage 1 — AI Tender Discovery.

Loads the large public tender dataset and filters it down to AI *candidates*
using the keyword vocabulary in keywords.py. This stage is deliberately
high-recall: it is fine (expected, even) for non-AI tenders like generic
"Smart City Platform" RFPs to slip through here. verify.py is what narrows
candidates down to confirmed AI tenders.
"""
from __future__ import annotations

import logging
from pathlib import Path

import duckdb
import pandas as pd

from src.discovery.keywords import primary_ai_types, scan_text

logger = logging.getLogger(__name__)

EXPECTED_COLUMNS = [
    "tender_id",
    "organisation",
    "state",
    "title",
    "tender_description",
    "tender_type",
    "date",
    "contract_value",
    "selected_bidder",
    "detail_url",
    "tender_document_url",
]


def load_tenders(parquet_path: Path) -> pd.DataFrame:
    """Load the raw tenders dataset from a local parquet file via DuckDB.

    DuckDB is used here (rather than pandas.read_parquet directly) so that
    the same code scales to querying larger-than-memory parquet files with
    SQL predicates, without changing the interface.
    """
    if not parquet_path.exists():
        raise FileNotFoundError(
            f"{parquet_path} not found. Run scripts/run_discovery.py --source huggingface "
            "first, or scripts/seed_demo_data.py for a synthetic dataset."
        )
    con = duckdb.connect()
    df = con.execute(f"SELECT * FROM read_parquet('{parquet_path.as_posix()}')").df()
    missing = [c for c in EXPECTED_COLUMNS if c not in df.columns]
    if missing:
        logger.warning("Dataset is missing expected columns: %s", missing)
    return df


def filter_candidates(df: pd.DataFrame) -> pd.DataFrame:
    """Apply the keyword filter across title + description.

    Returns a copy of df restricted to rows with at least one AI keyword hit,
    plus two new columns: `matched_ai_types` and `keyword_hit_count`.
    """
    titles = df.get("title", pd.Series([""] * len(df))).fillna("")
    descriptions = df.get("tender_description", pd.Series([""] * len(df))).fillna("")

    ai_types = []
    hit_counts = []
    is_match = []
    for title, desc in zip(titles, descriptions):
        combined = f"{title} {desc}"
        result = scan_text(combined)
        is_match.append(result.matched)
        ai_types.append(primary_ai_types(title, desc))
        hit_counts.append(len(result.matches))

    df = df.copy()
    df["is_ai_keyword_match"] = is_match
    df["matched_ai_types"] = ai_types
    df["keyword_hit_count"] = hit_counts

    candidates = df[df["is_ai_keyword_match"]].copy()
    candidates = candidates.sort_values("keyword_hit_count", ascending=False)
    logger.info(
        "Discovery: %d / %d tenders matched AI keywords (%.3f%%)",
        len(candidates),
        len(df),
        100 * len(candidates) / max(len(df), 1),
    )
    return candidates


def capability_map(candidates: pd.DataFrame) -> pd.DataFrame:
    """Aggregate candidates by AI type for the 'AI Capability Map' view.

    A tender can match more than one AI type, so this explodes the
    matched_ai_types list column before counting — the resulting counts
    can therefore sum to more than len(candidates).
    """
    exploded = candidates.explode("matched_ai_types")
    counts = (
        exploded.groupby("matched_ai_types")
        .size()
        .reset_index(name="tender_count")
        .sort_values("tender_count", ascending=False)
        .rename(columns={"matched_ai_types": "ai_type"})
    )
    return counts


def save_candidates(candidates: pd.DataFrame, out_path: Path) -> None:
    # matched_ai_types is a list column; parquet handles it, but store as
    # a delimited string too for easy SQL/UI filtering downstream.
    to_save = candidates.copy()
    to_save["matched_ai_types_str"] = to_save["matched_ai_types"].apply(
        lambda types: "|".join(types) if isinstance(types, list) else ""
    )
    to_save.to_parquet(out_path, index=False)
    logger.info("Saved %d candidates to %s", len(to_save), out_path)
