"""View 1 — AI Capability Map.

Generated directly from the discovered AI-tender dataset. Breaks results
down by AI type, and lets the user drill into State -> Department -> AI Type.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd
import plotly.express as px
import streamlit as st

import config
from src.storage import db

st.set_page_config(page_title="AI Capability Map", page_icon="🗺️", layout="wide")
st.title("🗺️ AI Capability Map")
st.caption("These numbers only reflect tenders that have run through the discovery + verification pipeline.")

if not config.SQLITE_DB_PATH.exists():
    st.warning("No data yet — run `python scripts/seed_demo_data.py` first.")
    st.stop()

tenders = db.list_confirmed_tenders(config.SQLITE_DB_PATH)
if not tenders:
    st.warning("No confirmed AI tenders in the database yet.")
    st.stop()

df = pd.DataFrame(tenders)

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("AI Procurement Discovery — by AI Type")
    type_counts = df.groupby("ai_type").size().reset_index(name="tender_count").sort_values("tender_count", ascending=False)
    fig = px.bar(type_counts, x="tender_count", y="ai_type", orientation="h",
                 labels={"tender_count": "Tenders", "ai_type": "AI Type"})
    fig.update_layout(yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("By Impact Level")
    impact_order = ["Very High", "High", "Moderate", "Low"]
    impact_counts = df.groupby("impact_level").size().reindex(impact_order).fillna(0).reset_index(name="tender_count")
    colors = {"Very High": "#d62728", "High": "#ff7f0e", "Moderate": "#f2c744", "Low": "#2ca02c"}
    fig2 = px.bar(impact_counts, x="impact_level", y="tender_count",
                  color="impact_level", color_discrete_map=colors,
                  labels={"tender_count": "Tenders", "impact_level": "Impact"})
    fig2.update_layout(showlegend=False)
    st.plotly_chart(fig2, use_container_width=True)

st.divider()
st.subheader("Drill down: State → Organisation → AI Type")

states = ["All"] + sorted(df["state"].dropna().unique().tolist())
selected_state = st.selectbox("State", states)

filtered = df if selected_state == "All" else df[df["state"] == selected_state]

st.dataframe(
    filtered[["tender_id", "title", "organisation", "state", "ai_type", "impact_level"]]
    .rename(columns={
        "tender_id": "Tender ID", "title": "Title", "organisation": "Organisation",
        "state": "State", "ai_type": "AI Type", "impact_level": "Impact",
    }),
    use_container_width=True,
    hide_index=True,
)

st.info("Click a tender ID on **View 2 — Tender Profile** to see its full governance breakdown.")
