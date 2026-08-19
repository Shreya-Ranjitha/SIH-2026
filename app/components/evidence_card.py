"""Reusable Streamlit component for rendering a single governance finding
with its evidence — the visual embodiment of the "evidence-first" design.
"""
from __future__ import annotations

import streamlit as st

from config import NOT_FOUND_MESSAGE

VERDICT_STYLE = {
    "FOUND": ("🟢", "Found"),
    "REQUIRED": ("🟢", "Required"),
    "OVERRIDE_AVAILABLE": ("🟢", "Override Available"),
    "UNCLEAR": ("🟡", "Unclear"),
    "NOT_FOUND": ("⚪", "Not Found"),
}

DIMENSION_LABELS = {
    "data_categories": "Data Categories",
    "human_oversight": "Human Oversight",
    "bias_fairness_testing": "Bias / Fairness Testing",
    "failure_fallback": "Failure & Fallback",
}


def render_verdict_badge(dimension: str, verdict: str) -> str:
    emoji, label = VERDICT_STYLE.get(verdict, ("⚪", verdict))
    dim_label = DIMENSION_LABELS.get(dimension, dimension)
    return f"{emoji} **{dim_label}** — {label}"


def render_evidence_card(finding, expanded: bool = False) -> None:
    """Render one GovernanceFinding (src.storage.models.GovernanceFinding) as a card."""
    emoji, label = VERDICT_STYLE.get(finding.verdict.value, ("⚪", finding.verdict.value))
    dim_label = DIMENSION_LABELS.get(finding.dimension, finding.dimension)

    with st.expander(f"{emoji} **{dim_label}** — {label}", expanded=expanded):
        if finding.summary:
            st.markdown(f"**Summary:** {finding.summary}")

        if finding.verdict.value == "NOT_FOUND" or not finding.evidence:
            st.info(NOT_FOUND_MESSAGE)
            return

        st.markdown("**Evidence:**")
        for ev in finding.evidence:
            location_bits = []
            if ev.clause:
                location_bits.append(f"Clause {ev.clause}")
            if ev.page:
                location_bits.append(f"Page {ev.page}")
            location = " · ".join(location_bits) if location_bits else "Location not specified"

            st.markdown(f"> {ev.snippet}")
            source = f" ({ev.source_document})" if ev.source_document else ""
            st.caption(f"📍 {location}{source}")
