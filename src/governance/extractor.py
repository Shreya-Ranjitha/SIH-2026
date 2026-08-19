"""Runs LLM structured extraction for each governance dimension across a
document's chunks, then merges per-chunk results into one GovernanceFinding
per dimension per tender.

Merge strategy: if ANY chunk reports a non-NOT_FOUND verdict, that verdict
(with its evidence) wins — a requirement documented anywhere in the tender
counts as documented. If ALL chunks report NOT_FOUND, the merged finding is
NOT_FOUND with no evidence, consistent with the "not found in the analyzed
document" framing.
"""
from __future__ import annotations

import json
import logging

from src.extraction.chunker import Chunk
from src.governance.schema import EXTRACTION_SYSTEM_PROMPT, build_user_prompt
from src.storage.models import Evidence, GovernanceFinding, Verdict

logger = logging.getLogger(__name__)

# Verdicts ranked by "how confirmed is this" — used to pick the best result
# across chunks. NOT_FOUND is always lowest priority.
_VERDICT_PRIORITY = {
    Verdict.REQUIRED: 3,
    Verdict.OVERRIDE_AVAILABLE: 3,
    Verdict.FOUND: 3,
    Verdict.UNCLEAR: 2,
    Verdict.NOT_FOUND: 1,
}


def _call_llm(client, model: str, dimension: str, chunk: Chunk) -> dict:
    user_prompt = build_user_prompt(dimension, chunk.text)
    response = client.messages.create(
        model=model,
        max_tokens=600,
        system=EXTRACTION_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )
    raw_text = "".join(block.text for block in response.content if hasattr(block, "text"))
    cleaned = raw_text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        logger.error("Could not parse extraction response for dimension=%s chunk=%d: %s",
                     dimension, chunk.chunk_index, raw_text)
        return {"verdict": "NOT_FOUND", "summary": "", "evidence": []}


def extract_dimension(client, model: str, tender_id: str, dimension: str,
                       chunks: list[Chunk], source_document: str) -> GovernanceFinding:
    """Run extraction for one governance dimension across all chunks and merge."""
    best_verdict = Verdict.NOT_FOUND
    best_priority = -1
    best_summary = ""
    best_evidence: list[Evidence] = []

    for chunk in chunks:
        parsed = _call_llm(client, model, dimension, chunk)
        try:
            verdict = Verdict(parsed.get("verdict", "NOT_FOUND"))
        except ValueError:
            verdict = Verdict.NOT_FOUND

        priority = _VERDICT_PRIORITY.get(verdict, 1)
        if priority > best_priority:
            best_priority = priority
            best_verdict = verdict
            best_summary = parsed.get("summary", "")
            if verdict != Verdict.NOT_FOUND:
                best_evidence = [
                    Evidence(
                        snippet=e.get("snippet", ""),
                        clause=e.get("clause"),
                        page=e.get("page"),
                        source_document=source_document,
                    )
                    for e in parsed.get("evidence", [])
                    if e.get("snippet")
                ]
            else:
                best_evidence = []

    if best_verdict == Verdict.NOT_FOUND:
        best_evidence = []  # enforce: never carry stray evidence on a NOT_FOUND verdict

    return GovernanceFinding(
        tender_id=tender_id,
        dimension=dimension,
        verdict=best_verdict,
        evidence=best_evidence,
        summary=best_summary,
    )


def extract_all_dimensions(client, model: str, tender_id: str, chunks: list[Chunk],
                            source_document: str) -> dict[str, GovernanceFinding]:
    from config import GOVERNANCE_DIMENSIONS

    findings = {}
    for dimension in GOVERNANCE_DIMENSIONS:
        findings[dimension] = extract_dimension(client, model, tender_id, dimension, chunks, source_document)
    return findings
