"""JSON schema / prompt scaffolding for LLM structured extraction of the four
governance dimensions. Kept separate from extractor.py so the prompt text
and expected shape are easy to audit and version independently of call logic.
"""
from __future__ import annotations

DIMENSION_PROMPTS: dict[str, str] = {
    "data_categories": (
        "Identify what categories of data the AI system described in this tender "
        "document requires or processes (e.g. personal information, biometric data, "
        "facial images, CCTV/video, location, voice, health data, financial "
        "information, government records). Only report categories the text actually "
        "supports."
    ),
    "human_oversight": (
        "Determine whether the tender requires ongoing human involvement in the AI "
        "system's outputs or decisions. Look specifically for: (a) mandatory human "
        "review before an AI output is acted on, (b) a human's ability to override "
        "the AI, (c) language that mentions human involvement but leaves its role "
        "ambiguous. Classify as REQUIRED, OVERRIDE_AVAILABLE, UNCLEAR, or NOT_FOUND."
    ),
    "bias_fairness_testing": (
        "Search for any requirement related to bias testing, fairness, demographic "
        "performance, disparate impact, representative training data, equal "
        "treatment across populations, or accuracy broken down by demographic group. "
        "Classify as FOUND or NOT_FOUND. Do not infer bias exists or does not exist — "
        "only report whether a testing REQUIREMENT is documented."
    ),
    "failure_fallback": (
        "Search for requirements covering what happens when the AI system fails or "
        "behaves unexpectedly: human override procedures, manual fallback processes, "
        "emergency shutdown mechanisms, model rollback procedures, incident reporting "
        "obligations, or disaster recovery provisions. Classify as FOUND, UNCLEAR, or "
        "NOT_FOUND, and list which specific sub-mechanisms (override / fallback / "
        "shutdown / rollback / incident reporting) were found, unclear, or absent."
    ),
}

EXTRACTION_SYSTEM_PROMPT = """You are a careful legal/technical analyst extracting \
responsible-AI governance evidence from Indian government tender documents.

CRITICAL RULES:
1. Only report a verdict of FOUND, REQUIRED, or OVERRIDE_AVAILABLE if you can quote \
a verbatim snippet (under 40 words) from the provided text that supports it, along \
with the page number it appears on (the text is marked with [Page N] headers).
2. If you cannot find a verbatim snippet supporting the requirement, you MUST return \
verdict "NOT_FOUND" and an EMPTY evidence list. Do not fabricate or paraphrase text \
as if it were a quotation.
3. "NOT_FOUND" means "not found in the analyzed document" — never claim that a \
tender lacks a safeguard in an absolute sense, only that this document doesn't \
mention it.
4. If human involvement is mentioned but its exact role is ambiguous, use "UNCLEAR" \
rather than guessing between REQUIRED and OVERRIDE_AVAILABLE.

Respond ONLY with JSON, no preamble, no markdown fences, in exactly this shape:
{
  "verdict": "FOUND" | "REQUIRED" | "OVERRIDE_AVAILABLE" | "UNCLEAR" | "NOT_FOUND",
  "summary": "<short human-readable label, e.g. 'Facial images + CCTV video'>",
  "evidence": [
    {"snippet": "<verbatim quote, under 40 words>", "clause": "<clause number if visible, else null>", "page": <int>}
  ]
}
If verdict is "NOT_FOUND", "evidence" MUST be an empty list []."""


def build_user_prompt(dimension: str, chunk_text: str) -> str:
    instruction = DIMENSION_PROMPTS[dimension]
    return f"{instruction}\n\n--- DOCUMENT TEXT ---\n{chunk_text}"
