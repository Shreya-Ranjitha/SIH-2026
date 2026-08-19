"""SQLite persistence for confirmed tenders and governance findings.

Deliberately plain sqlite3 (no ORM) for MVP transparency — every row that
backs a dashboard claim can be inspected with `sqlite3 data/processed/evidence.db`.
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from src.storage.models import ConfirmedAITender, Evidence, GovernanceFinding, ImpactLevel, TenderProfile, Verdict

SCHEMA = """
CREATE TABLE IF NOT EXISTS confirmed_tenders (
    tender_id TEXT PRIMARY KEY,
    organisation TEXT,
    state TEXT,
    title TEXT,
    ai_type TEXT,
    confidence TEXT,
    verification_reasoning TEXT,
    is_priority INTEGER DEFAULT 0,
    impact_level TEXT,
    impact_reasoning TEXT
);

CREATE TABLE IF NOT EXISTS governance_findings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tender_id TEXT NOT NULL,
    dimension TEXT NOT NULL,
    verdict TEXT NOT NULL,
    summary TEXT,
    FOREIGN KEY (tender_id) REFERENCES confirmed_tenders(tender_id),
    UNIQUE(tender_id, dimension)
);

CREATE TABLE IF NOT EXISTS evidence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    finding_id INTEGER NOT NULL,
    snippet TEXT NOT NULL,
    clause TEXT,
    page INTEGER,
    source_document TEXT,
    FOREIGN KEY (finding_id) REFERENCES governance_findings(id)
);
"""


@contextmanager
def get_connection(db_path: Path):
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    try:
        yield con
        con.commit()
    finally:
        con.close()


def init_db(db_path: Path) -> None:
    with get_connection(db_path) as con:
        con.executescript(SCHEMA)


def upsert_confirmed_tender(db_path: Path, tender: ConfirmedAITender, impact_level: ImpactLevel | None = None,
                             impact_reasoning: str = "") -> None:
    with get_connection(db_path) as con:
        con.execute(
            """
            INSERT INTO confirmed_tenders
                (tender_id, organisation, state, title, ai_type, confidence,
                 verification_reasoning, is_priority, impact_level, impact_reasoning)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(tender_id) DO UPDATE SET
                organisation=excluded.organisation,
                state=excluded.state,
                title=excluded.title,
                ai_type=excluded.ai_type,
                confidence=excluded.confidence,
                verification_reasoning=excluded.verification_reasoning,
                is_priority=excluded.is_priority,
                impact_level=excluded.impact_level,
                impact_reasoning=excluded.impact_reasoning
            """,
            (
                tender.tender_id, tender.organisation, tender.state, tender.title,
                tender.ai_type, tender.confidence, tender.verification_reasoning,
                int(tender.is_priority),
                impact_level.value if impact_level else None,
                impact_reasoning,
            ),
        )


def save_finding(db_path: Path, finding: GovernanceFinding) -> int:
    with get_connection(db_path) as con:
        cur = con.execute(
            """
            INSERT INTO governance_findings (tender_id, dimension, verdict, summary)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(tender_id, dimension) DO UPDATE SET
                verdict=excluded.verdict, summary=excluded.summary
            """,
            (finding.tender_id, finding.dimension, finding.verdict.value, finding.summary),
        )
        # Fetch the finding id (works whether inserted or updated)
        row = con.execute(
            "SELECT id FROM governance_findings WHERE tender_id=? AND dimension=?",
            (finding.tender_id, finding.dimension),
        ).fetchone()
        finding_id = row["id"]

        # Replace evidence rows for this finding
        con.execute("DELETE FROM evidence WHERE finding_id=?", (finding_id,))
        for ev in finding.evidence:
            con.execute(
                "INSERT INTO evidence (finding_id, snippet, clause, page, source_document) VALUES (?, ?, ?, ?, ?)",
                (finding_id, ev.snippet, ev.clause, ev.page, ev.source_document),
            )
        return finding_id


def load_tender_profile(db_path: Path, tender_id: str) -> TenderProfile | None:
    with get_connection(db_path) as con:
        trow = con.execute("SELECT * FROM confirmed_tenders WHERE tender_id=?", (tender_id,)).fetchone()
        if trow is None:
            return None

        findings: dict[str, GovernanceFinding] = {}
        frows = con.execute("SELECT * FROM governance_findings WHERE tender_id=?", (tender_id,)).fetchall()
        for frow in frows:
            erows = con.execute("SELECT * FROM evidence WHERE finding_id=?", (frow["id"],)).fetchall()
            evidence = [
                Evidence(snippet=e["snippet"], clause=e["clause"], page=e["page"], source_document=e["source_document"])
                for e in erows
            ]
            findings[frow["dimension"]] = GovernanceFinding(
                tender_id=tender_id,
                dimension=frow["dimension"],
                verdict=Verdict(frow["verdict"]),
                evidence=evidence,
                summary=frow["summary"] or "",
            )

        return TenderProfile(
            tender_id=trow["tender_id"],
            title=trow["title"],
            organisation=trow["organisation"],
            state=trow["state"],
            ai_type=trow["ai_type"],
            impact_level=ImpactLevel(trow["impact_level"]) if trow["impact_level"] else ImpactLevel.LOW,
            impact_reasoning=trow["impact_reasoning"] or "",
            findings=findings,
        )


def list_confirmed_tenders(db_path: Path):
    with get_connection(db_path) as con:
        return [dict(row) for row in con.execute("SELECT * FROM confirmed_tenders ORDER BY impact_level, title").fetchall()]
