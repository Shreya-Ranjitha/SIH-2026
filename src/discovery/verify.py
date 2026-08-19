"""Second-stage AI verification.

A keyword hit is not automatically treated as a genuine AI procurement.
"Smart City Platform" may contain no real AI. "Intelligent Surveillance
System" may hide computer vision / facial recognition inside its technical
specification. This module makes the candidate -> confirmed decision using
an LLM call over the available metadata (title + description), and — where
a tender document has already been fetched — the extracted document text.

This is the boundary at which the system's evidence-first philosophy starts:
the verification verdict itself is stored with the reasoning that produced it.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from src.storage.models import TenderCandidate

logger = logging.getLogger(__name__)

VERIFY_SYSTEM_PROMPT = """You are verifying whether a government tender genuinely \
involves an AI/ML-based system, as opposed to merely containing an AI-adjacent buzzword \
in its title (e.g. "Smart City Platform" often has no real AI component).

Respond ONLY with JSON, no preamble, no markdown fences, in exactly this shape:
{
  "is_ai_confirmed": true or false,
  "confidence": "high" | "medium" | "low",
  "ai_type": "<one of: Computer Vision, Facial Recognition, Conversational AI, \
Generative AI / LLM, Predictive Analytics, NLP, AI / Machine Learning, Not AI>",
  "reasoning": "<one or two sentence justification, referencing the actual text>"
}"""


@dataclass
class VerificationResult:
    tender_id: str
    is_ai_confirmed: bool
    confidence: str
    ai_type: str
    reasoning: str


def _build_user_prompt(candidate: TenderCandidate, document_excerpt: str | None) -> str:
    parts = [
        f"Title: {candidate.title}",
        f"Description: {candidate.tender_description}",
        f"Matched keywords suggested types: {', '.join(candidate.matched_ai_types)}",
    ]
    if document_excerpt:
        parts.append(f"Tender document excerpt:\n{document_excerpt[:4000]}")
    return "\n\n".join(parts)


def verify_candidate(
    candidate: TenderCandidate,
    document_excerpt: str | None = None,
    client=None,
    model: str = "claude-sonnet-4-6",
) -> VerificationResult:
    """Call the LLM to confirm/deny whether a candidate is genuinely AI-related.

    `client` is an anthropic.Anthropic() instance, injected so this function
    stays testable without a live API key. If no client is supplied, this
    raises — callers should catch and fall back to manual review.
    """
    if client is None:
        raise RuntimeError(
            "verify_candidate requires an anthropic.Anthropic() client. "
            "See scripts/run_discovery.py for wiring, or config.ANTHROPIC_API_KEY."
        )

    user_prompt = _build_user_prompt(candidate, document_excerpt)
    response = client.messages.create(
        model=model,
        max_tokens=400,
        system=VERIFY_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )
    raw_text = "".join(block.text for block in response.content if hasattr(block, "text"))
    cleaned = raw_text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        logger.error("Could not parse verification response for %s: %s", candidate.tender_id, raw_text)
        return VerificationResult(
            tender_id=candidate.tender_id,
            is_ai_confirmed=False,
            confidence="low",
            ai_type="Not AI",
            reasoning="Verification response could not be parsed; defaulting to unconfirmed.",
        )

    return VerificationResult(
        tender_id=candidate.tender_id,
        is_ai_confirmed=bool(parsed.get("is_ai_confirmed", False)),
        confidence=parsed.get("confidence", "low"),
        ai_type=parsed.get("ai_type", "Not AI"),
        reasoning=parsed.get("reasoning", ""),
    )
