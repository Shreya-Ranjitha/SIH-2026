"""Shared dataclasses used across discovery, extraction, governance, and the app.

Kept dependency-free (stdlib only) so they can be imported from anywhere,
including Streamlit pages, without pulling in DuckDB/PDF/LLM dependencies.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum


class ImpactLevel(str, Enum):
    LOW = "Low"
    MODERATE = "Moderate"
    HIGH = "High"
    VERY_HIGH = "Very High"


class Verdict(str, Enum):
    FOUND = "FOUND"
    REQUIRED = "REQUIRED"
    OVERRIDE_AVAILABLE = "OVERRIDE_AVAILABLE"
    UNCLEAR = "UNCLEAR"
    NOT_FOUND = "NOT_FOUND"


@dataclass
class TenderCandidate:
    """A tender that matched the Stage 1 keyword filter (not yet confirmed)."""

    tender_id: str
    organisation: str
    state: str | None
    title: str
    tender_description: str
    tender_type: str | None
    tender_date: date | None
    contract_value: float | None
    detail_url: str | None
    tender_document_url: str | None
    matched_ai_types: list[str] = field(default_factory=list)
    keyword_hit_count: int = 0


@dataclass
class ConfirmedAITender:
    """A candidate that passed Stage-1 LLM verification."""

    tender_id: str
    organisation: str
    state: str | None
    title: str
    ai_type: str
    confidence: str
    verification_reasoning: str
    is_priority: bool = False  # selected for Stage 2 curated deep-dive


@dataclass
class Evidence:
    """A single piece of supporting evidence for a governance verdict.

    `clause` and `page` are optional because some documents lack numbered
    clauses (e.g. plain-text corrigenda), but `snippet` should always be a
    verbatim excerpt when the verdict is not NOT_FOUND.
    """

    snippet: str
    clause: str | None = None
    page: int | None = None
    source_document: str | None = None


@dataclass
class GovernanceFinding:
    """One governance dimension's result for one tender.

    Structurally enforces the evidence-first rule: a FOUND/REQUIRED/UNCLEAR
    verdict must carry at least one Evidence entry; NOT_FOUND must not
    fabricate one.
    """

    tender_id: str
    dimension: str  # one of config.GOVERNANCE_DIMENSIONS
    verdict: Verdict
    evidence: list[Evidence] = field(default_factory=list)
    summary: str = ""  # short human-readable label, e.g. "Facial images + CCTV video"

    def __post_init__(self):
        if self.verdict == Verdict.NOT_FOUND and self.evidence:
            raise ValueError(
                "GovernanceFinding with verdict NOT_FOUND must not carry fabricated evidence."
            )
        if self.verdict != Verdict.NOT_FOUND and not self.evidence:
            raise ValueError(
                f"GovernanceFinding with verdict {self.verdict} requires at least one Evidence entry."
            )


@dataclass
class TenderProfile:
    """Full governance profile for one confirmed AI tender — feeds View 2 & View 3."""

    tender_id: str
    title: str
    organisation: str
    state: str | None
    ai_type: str
    impact_level: ImpactLevel
    impact_reasoning: str
    findings: dict[str, GovernanceFinding] = field(default_factory=dict)
