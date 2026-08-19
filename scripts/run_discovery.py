#!/usr/bin/env python
"""CLI entrypoint for Stage 1 — AI Tender Discovery against the real dataset.

Usage:
    python scripts/run_discovery.py --source huggingface --dataset rumourscape/tenders
    python scripts/run_discovery.py --source local --path ./data/raw/tenders.parquet
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from src.discovery.filter import capability_map, filter_candidates, load_tenders, save_candidates

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def download_from_huggingface(dataset_name: str, out_path: Path) -> None:
    """Downloads the dataset via the `datasets` library and writes it to parquet locally."""
    from datasets import load_dataset

    logger.info("Downloading %s from Hugging Face...", dataset_name)
    ds = load_dataset(dataset_name, split="train", token=config.HF_TOKEN)
    df = ds.to_pandas()
    df.to_parquet(out_path, index=False)
    logger.info("Saved %d rows to %s", len(df), out_path)


def main():
    parser = argparse.ArgumentParser(description="Stage 1: AI Tender Discovery")
    parser.add_argument("--source", choices=["huggingface", "local"], default="local")
    parser.add_argument("--dataset", default=config.HF_DATASET_NAME, help="HF dataset name")
    parser.add_argument("--path", type=Path, default=config.RAW_TENDERS_PARQUET,
                         help="Local parquet path to read from / write to")
    args = parser.parse_args()

    if args.source == "huggingface":
        download_from_huggingface(args.dataset, args.path)

    df = load_tenders(args.path)
    candidates = filter_candidates(df)
    save_candidates(candidates, config.CANDIDATES_PARQUET)

    print("\n=== AI Capability Map ===")
    print(capability_map(candidates).to_string(index=False))
    print(f"\n{len(candidates)} / {len(df)} tenders matched the AI keyword filter.")
    print(f"Candidates saved to {config.CANDIDATES_PARQUET}")
    print("Next: python scripts/run_extraction.py --top-n 20 --priority-only")


if __name__ == "__main__":
    main()
