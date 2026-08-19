"""Central configuration for the AI Government Tender Evidence Explorer."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# --- Paths -------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
DOCUMENTS_DIR = DATA_DIR / "documents"

for _dir in (RAW_DIR, PROCESSED_DIR, DOCUMENTS_DIR):
    _dir.mkdir(parents=True, exist_ok=True)

RAW_TENDERS_PARQUET = RAW_DIR / "tenders.parquet"
CANDIDATES_PARQUET = PROCESSED_DIR / "ai_candidates.parquet"
CONFIRMED_PARQUET = PROCESSED_DIR / "ai_confirmed.parquet"
SQLITE_DB_PATH = Path(os.getenv("SQLITE_DB_PATH", PROCESSED_DIR / "evidence.db"))

# --- Dataset -------------------------------------------------------------
HF_DATASET_NAME = "rumourscape/tenders"
HF_TOKEN = os.getenv("HUGGINGFACE_TOKEN") or None

# --- LLM -------------------------------------------------------------
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")

# --- Curated deep-dive -------------------------------------------------------------
DEEP_DIVE_TOP_N = 20

# --- Governance dimensions -------------------------------------------------------------
GOVERNANCE_DIMENSIONS = [
    "data_categories",
    "human_oversight",
    "bias_fairness_testing",
    "failure_fallback",
]

# Verdict vocabulary shared across dimensions (kept intentionally small & explainable)
VERDICT_FOUND = "FOUND"
VERDICT_REQUIRED = "REQUIRED"
VERDICT_OVERRIDE_AVAILABLE = "OVERRIDE_AVAILABLE"
VERDICT_UNCLEAR = "UNCLEAR"
VERDICT_NOT_FOUND = "NOT_FOUND"

NOT_FOUND_MESSAGE = "No explicit requirement was identified in the analyzed document."
