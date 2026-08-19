"""View 3 — Evidence Explorer.

The central demonstration of the platform's evidence-first methodology:
click a governance verdict, see the exact clause/page/snippet — or, for
NOT_FOUND, the explicit "not found in the analyzed document" message.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st

import config
from app.components.evidence_card import render_evidence_card
from src.storage import db

st.set_page_config(page_title="Evidence Explorer", page_icon="🧾", layout="wide")
st.title("🧾 Evidence Explorer")
st.caption("Every finding here is traceable to its source. \"Not found\" means "
           "*not found in the analyzed document* — never an accusation.")

if not config.SQLITE_DB_PATH.exists():
    st.warning("No data yet — run `python scripts/seed_demo_data.py` first.")
    st.stop()

tenders = db.list_confirmed_tenders(config.SQLITE_DB_PATH)
if not tenders:
    st.warning("No confirmed AI tenders in the database yet.")
    st.stop()

id_to_title = {t["tender_id"]: f"{t['title']} — {t['organisation']} ({t['state']})" for t in tenders}
selected_id = st.selectbox(
    "Select a tender",
    options=list(id_to_title.keys()),
    format_func=lambda tid: id_to_title[tid],
)

profile = db.load_tender_profile(config.SQLITE_DB_PATH, selected_id)
if profile is None:
    st.error("Could not load this tender's profile.")
    st.stop()

st.subheader(profile.title)
st.caption(f"{profile.organisation} · {profile.state or '—'} · {profile.ai_type} · Impact: {profile.impact_level.value}")

st.divider()

for dimension in config.GOVERNANCE_DIMENSIONS:
    finding = profile.findings.get(dimension)
    if finding is None:
        continue
    render_evidence_card(finding, expanded=True)

st.divider()
st.markdown(
    "**Not Found ≠ Doesn't Exist.** This prevents the system from making unsupported "
    "claims based on absence of evidence — a governance requirement may exist elsewhere "
    "in a document set that wasn't analyzed, or in a corrigendum issued later."
)
