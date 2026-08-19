# AI Government Tender Evidence Explorer

> A platform that mines millions of real Indian government tender records to identify
> AI-related procurements, then analyzes the underlying tender documents to show exactly
> what data use, human oversight, testing, and failure safeguards are documented —
> with every finding traceable to its source.

**Core differentiator:** We don't score whether government AI is responsible — we show
the evidence for what the government actually required. "Not found" always means
*"not found in the analyzed document,"* never *"doesn't exist."*

---

## Pipeline

```
Millions of Tender Records (rumourscape/tenders, CC BY 4.0)
        ↓
Stage 1 — AI Tender Discovery      (keyword + semantic filter, DuckDB/Pandas)
        ↓
Stage 2 — Curated Deep-Dive        (select ~15-20 high-priority candidates)
        ↓
Stage 3 — Document Extraction      (PDF/OCR → chunks → LLM structured extraction)
        ↓
Governance Evidence Extraction     (Data / Human Oversight / Bias Testing / Failure & Fallback)
        ↓
Impact Classification              (deterministic, rule-based: Low/Moderate/High/Very High)
        ↓
Evidence-Linked Streamlit Dashboard
```

## Project layout

```
ai-tender-evidence-explorer/
├── src/
│   ├── discovery/        # Stage 1: keyword + semantic AI-tender filtering
│   │   ├── keywords.py       # AI vocabulary + regex matching
│   │   ├── filter.py         # DuckDB/Pandas candidate filtering
│   │   └── verify.py         # LLM-based "is this actually AI?" verification
│   ├── extraction/        # Stage 3: turning tender PDFs into clean text chunks
│   │   ├── pdf_extract.py    # PyMuPDF / pdfplumber text extraction
│   │   ├── ocr_fallback.py   # OCR for scanned PDFs
│   │   └── chunker.py        # Page-aware chunking for LLM extraction
│   ├── governance/        # Governance evidence extraction + impact classification
│   │   ├── schema.py         # Structured-output schema (Pydantic-style dataclasses)
│   │   ├── extractor.py      # LLM structured extraction over chunks
│   │   └── impact_classifier.py  # Deterministic Low/Moderate/High/Very High rules
│   ├── storage/
│   │   ├── db.py             # SQLite persistence layer
│   │   └── models.py         # Row/record dataclasses shared across the app
│   └── pipeline.py        # Orchestrates discovery → extraction → governance → storage
├── app/
│   ├── streamlit_app.py           # Landing page / navigation
│   └── pages/
│       ├── 1_AI_Capability_Map.py     # View 1 — discovery-wide dashboard
│       ├── 2_Tender_Profile.py        # View 2 — single-tender governance summary
│       └── 3_Evidence_Explorer.py     # View 3 — clause-level evidence drill-down
├── scripts/
│   ├── seed_demo_data.py   # Generates a small synthetic dataset so the app runs with no internet
│   ├── run_discovery.py    # CLI: run Stage 1 discovery against a tenders dataset
│   └── run_extraction.py   # CLI: run Stage 3 extraction over selected tenders
├── tests/
│   └── test_keywords.py
├── config.py
├── requirements.txt
└── .env.example
```

## Quickstart (demo mode, no internet / no dataset download required)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 1. Generate a small synthetic tender dataset + fake governance evidence
#    so the dashboard has something to show immediately.
python scripts/seed_demo_data.py

# 2. Launch the dashboard
streamlit run app/streamlit_app.py
```

## Running against the real dataset

```bash
# Downloads / loads rumourscape/tenders from Hugging Face into data/raw/tenders.parquet
python scripts/run_discovery.py --source huggingface --dataset rumourscape/tenders

# Pick candidates flagged as high-priority, fetch their tender documents,
# run OCR/extraction, and populate the governance evidence database.
python scripts/run_extraction.py --top-n 20 --priority-only
```

Set `ANTHROPIC_API_KEY` in a `.env` file (see `.env.example`) before running the
verification (`src/discovery/verify.py`) and extraction (`src/governance/extractor.py`)
stages — both call the Claude API for structured extraction.

## Design principles this codebase enforces

1. **Keyword match ≠ confirmed AI tender.** `discovery/filter.py` only produces
   *candidates*; `discovery/verify.py` is a required second pass before a tender is
   marked `is_ai_confirmed = True`.
2. **Every governance verdict carries evidence.** `governance/schema.py` makes it
   structurally impossible to store a verdict without a `clause`, `page`, and
   `evidence_snippet` (or an explicit `NOT_FOUND` status with no fabricated snippet).
3. **Impact classification is deterministic and inspectable**, not another LLM score —
   see `governance/impact_classifier.py`.
4. **"Not found" is a first-class status**, not an error state — the UI always renders
   it as *"No explicit requirement was identified in the analyzed document,"* never as
   an accusation.

## What this MVP intentionally does NOT do

- Scrape live procurement portals (CPPP/GeM) or bypass CAPTCHAs
- Crawl state-by-state in real time
- Build vendor network graphs or tender lifecycle/corrigendum tracking
- Send subscriptions/alerts

These are listed as future scope once the discovery → evidence pipeline is validated.

## License

Dataset: `rumourscape/tenders` is distributed under CC BY 4.0. This codebase is provided
as-is for the Smart India Hackathon (SIH) submission.
