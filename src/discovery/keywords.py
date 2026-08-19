"""AI vocabulary and keyword-matching logic for Stage 1 discovery.

Keyword match is intentionally a *high-recall, low-precision* first pass.
Every hit here is only a "candidate" — verify.py performs the second-stage
check before anything is marked as a confirmed AI tender.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# Grouped so the UI ("AI Capability Map") can bucket tenders by AI type.
AI_KEYWORD_GROUPS: dict[str, list[str]] = {
    "AI / Machine Learning": [
        "artificial intelligence",
        r"\bai\b",
        r"\bai/ml\b",
        "machine learning",
        "deep learning",
        "neural network",
    ],
    "Generative AI / LLM": [
        "generative ai",
        r"\bgenai\b",
        r"\bllm\b",
        "large language model",
        "chatbot",
        "conversational ai",
    ],
    "Computer Vision": [
        "computer vision",
        "object detection",
        "video analytics",
        "image recognition",
    ],
    "Facial Recognition": [
        "facial recognition",
        "facial identification",
        "face recognition",
        "biometric identification",
    ],
    "NLP": [
        "natural language processing",
        r"\bnlp\b",
        "speech recognition",
        "text mining",
    ],
    "Predictive / Automated Decisions": [
        "predictive analytics",
        "automated decision",
        "decision support system",
        "risk scoring",
    ],
}

# Flat vocabulary, used for quick single-pass scanning.
ALL_KEYWORDS: list[str] = [kw for group in AI_KEYWORD_GROUPS.values() for kw in group]


@dataclass
class KeywordMatch:
    """A single keyword hit within a piece of text."""

    keyword: str
    ai_type: str
    span: tuple[int, int]


@dataclass
class MatchResult:
    text: str
    matches: list[KeywordMatch] = field(default_factory=list)

    @property
    def matched(self) -> bool:
        return len(self.matches) > 0

    @property
    def ai_types(self) -> list[str]:
        # Preserve order, de-duplicate
        seen = []
        for m in self.matches:
            if m.ai_type not in seen:
                seen.append(m.ai_type)
        return seen


def _compiled_patterns() -> list[tuple[str, str, re.Pattern]]:
    compiled = []
    for ai_type, keywords in AI_KEYWORD_GROUPS.items():
        for kw in keywords:
            pattern = kw if kw.startswith(r"\b") or "\\b" in kw else re.escape(kw)
            compiled.append((kw, ai_type, re.compile(pattern, re.IGNORECASE)))
    return compiled


_PATTERNS = _compiled_patterns()


def scan_text(text: str) -> MatchResult:
    """Scan a single string (e.g. title + description) for AI keywords."""
    result = MatchResult(text=text)
    if not text:
        return result
    for kw, ai_type, pattern in _PATTERNS:
        for m in pattern.finditer(text):
            result.matches.append(KeywordMatch(keyword=kw, ai_type=ai_type, span=m.span()))
    return result


def is_candidate(title: str, description: str) -> bool:
    """Quick boolean check used for filtering large dataframes."""
    combined = f"{title or ''} {description or ''}"
    return scan_text(combined).matched


def primary_ai_types(title: str, description: str) -> list[str]:
    combined = f"{title or ''} {description or ''}"
    return scan_text(combined).ai_types
