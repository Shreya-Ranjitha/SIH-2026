"""Deterministic, rule-based impact classification.

Intentionally NOT an LLM call: the pitch's core differentiator is that this
system does not produce an opaque AI-generated score. The impact level a
tender receives should always be traceable to a plain if/elif rule, not a
model's judgment call.
"""
from __future__ import annotations

from src.storage.models import ImpactLevel

# Ordered most-specific-first: the first matching rule wins.
_VERY_HIGH_AI_TYPES = {
    "Facial Recognition",
    "Biometric Identification",
}
_VERY_HIGH_KEYWORDS = [
    "facial recognition",
    "biometric identification",
    "automated welfare",
    "welfare eligibility",
    "law enforcement",
    "predictive policing",
]

_HIGH_KEYWORDS = [
    "recruitment screening",
    "eligibility assessment",
    "healthcare prioritization",
    "healthcare prioritisation",
    "credit scoring",
    "loan approval",
    "surveillance",
]

_MODERATE_AI_TYPES = {
    "Conversational AI",
    "Predictive Analytics",
    "Predictive / Automated Decisions",
}
_MODERATE_KEYWORDS = [
    "chatbot",
    "traffic prediction",
    "decision support",
    "decision-support",
    "citizen service",
    "citizen-service",
]

_LOW_KEYWORDS = [
    "document summarization",
    "document summarisation",
    "internal search",
    "administrative automation",
    "office automation",
]


def classify_impact(ai_type: str, title: str, description: str) -> tuple[ImpactLevel, str]:
    """Return (impact_level, human-readable reasoning) using plain rule matching.

    Rules are checked in strict priority order: Very High > High > Moderate > Low.
    If nothing matches, defaults to Moderate with a reasoning note flagging it
    for manual review — the system never silently assumes "Low" for an
    unrecognized AI use case.
    """
    combined = f"{title or ''} {description or ''}".lower()

    if ai_type in _VERY_HIGH_AI_TYPES:
        return ImpactLevel.VERY_HIGH, f"AI type '{ai_type}' is classified Very High impact by default."
    for kw in _VERY_HIGH_KEYWORDS:
        if kw in combined:
            return ImpactLevel.VERY_HIGH, f"Matched Very High impact keyword: '{kw}'."

    for kw in _HIGH_KEYWORDS:
        if kw in combined:
            return ImpactLevel.HIGH, f"Matched High impact keyword: '{kw}'."

    if ai_type in _MODERATE_AI_TYPES:
        return ImpactLevel.MODERATE, f"AI type '{ai_type}' is classified Moderate impact by default."
    for kw in _MODERATE_KEYWORDS:
        if kw in combined:
            return ImpactLevel.MODERATE, f"Matched Moderate impact keyword: '{kw}'."

    for kw in _LOW_KEYWORDS:
        if kw in combined:
            return ImpactLevel.LOW, f"Matched Low impact keyword: '{kw}'."

    return (
        ImpactLevel.MODERATE,
        "No specific impact keyword matched; defaulted to Moderate pending manual review.",
    )
