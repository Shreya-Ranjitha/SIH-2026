"""View 2 — Tender Profile.

Shows one tender's summary card: org, state, AI type, impact level, and a
governance-dimension table with FOUND / UNCLEAR / NOT_FOUND at a glance.
Each row links into View 3 — Evidence Explorer.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st

import config
from app.components.evidence_card import DIMENSION_LABELS, VERDICT_STYLE
from src.storage import db

st.set_page_config(page_title="Tender Profile", page_icon="📋", layout="wide")
st.title("📋 Tender Profile")

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

impact_colors = {"Very High": "🔴", "High": "🟠", "Moderate": "🟡", "Low": "🟢"}
impact_emoji = impact_colors.get(profile.impact_level.value, "⚪")

st.header(profile.title)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Organisation", profile.organisation)
c2.metric("State", profile.state or "—")
c3.metric("AI Type", profile.ai_type)
c4.metric("Impact", f"{impact_emoji} {profile.impact_level.value}")

st.caption(f"**Why this impact level:** {profile.impact_reasoning}")

st.divider()
st.subheader("Governance Dimensions")

rows = []
for dimension in config.GOVERNANCE_DIMENSIONS:
    finding = profile.findings.get(dimension)
    if finding is None:
        emoji, label = "⚪", "Not Analyzed"
        summary = "This dimension has not been extracted for this tender yet."
    else:
        emoji, label = VERDICT_STYLE.get(finding.verdict.value, ("⚪", finding.verdict.value))
        summary = finding.summary or ""
    rows.append({
        "Dimension": DIMENSION_LABELS.get(dimension, dimension),
        "Result": f"{emoji} {label}",
        "Summary": summary,
    })

st.table(rows)

st.info(
    "👉 Open **View 3 — Evidence Explorer** and select this tender to see the exact "
    "clause and page behind each verdict above."
)

st.page_link("pages/3_Evidence_Explorer.py", label="Go to Evidence Explorer", icon="🧾")
