"""Landing page for the AI Government Tender Evidence Explorer.

Run with: streamlit run app/streamlit_app.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

import config
from src.storage import db

st.set_page_config(
    page_title="AI Government Tender Evidence Explorer",
    page_icon="🔎",
    layout="wide",
)

st.title("🔎 AI Government Tender Evidence Explorer")
st.markdown(
    "> A platform that mines millions of real Indian government tender records to "
    "identify AI-related procurements, then analyzes the underlying tender documents "
    "to show exactly what data use, human oversight, testing, and failure safeguards "
    "are documented — with every finding traceable to its source."
)

st.divider()

col1, col2, col3 = st.columns(3)

if config.SQLITE_DB_PATH.exists():
    tenders = db.list_confirmed_tenders(config.SQLITE_DB_PATH)
else:
    tenders = []

with col1:
    st.metric("Confirmed AI Tenders", len(tenders))
with col2:
    very_high = sum(1 for t in tenders if t.get("impact_level") == "Very High")
    st.metric("Very High Impact", very_high)
with col3:
    states = len({t.get("state") for t in tenders if t.get("state")})
    st.metric("States Represented", states)

st.divider()

if not tenders:
    st.warning(
        "No data loaded yet. Run `python scripts/seed_demo_data.py` for a synthetic "
        "demo dataset, or `python scripts/run_discovery.py` + "
        "`python scripts/run_extraction.py` against the real dataset."
    )
else:
    st.markdown("### Explore")
    st.page_link("pages/1_AI_Capability_Map.py", label="View 1 — AI Capability Map", icon="🗺️")
    st.page_link("pages/2_Tender_Profile.py", label="View 2 — Tender Profile", icon="📋")
    st.page_link("pages/3_Evidence_Explorer.py", label="View 3 — Evidence Explorer", icon="🧾")

st.divider()
st.caption(
    "Core differentiator: we don't score whether government AI is responsible — "
    "we show the evidence for what the government actually required. "
    "\"Not found\" always means *not found in the analyzed document*, never *doesn't exist*."
)
