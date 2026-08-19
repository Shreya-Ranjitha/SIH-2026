#!/usr/bin/env python
"""Generate a small synthetic dataset so the dashboard runs end-to-end with
no internet access and no Anthropic API key — useful for local dev, demos,
and CI. Mirrors the shape of the real rumourscape/tenders dataset and the
governance evidence a full pipeline run would produce.

Run: python scripts/seed_demo_data.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import random

import pandas as pd

import config
from src.discovery.filter import capability_map, filter_candidates
from src.governance.impact_classifier import classify_impact
from src.storage import db
from src.storage.models import ConfirmedAITender, Evidence, GovernanceFinding, Verdict

random.seed(42)

STATES = ["Tamil Nadu", "Karnataka", "Maharashtra", "Delhi", "Telangana", "Uttar Pradesh", "Kerala", "Gujarat"]
ORGS = [
    "State Police Department", "Municipal Corporation", "State Health Department",
    "State Transport Corporation", "Urban Development Authority", "State Welfare Board",
    "Smart City Mission Office", "State Revenue Department",
]

# (title, description, tender_type, is_ai_relevant)
RAW_TENDER_TEMPLATES = [
    ("AI-Based Facial Recognition System for Public Surveillance",
     "Supply, installation and maintenance of an AI-powered facial recognition and video "
     "analytics system across CCTV networks for law enforcement identification purposes.",
     "Goods & Services", True),
    ("Chatbot for Citizen Grievance Redressal",
     "Development of a conversational AI / NLP based chatbot to handle citizen grievances "
     "and route them to the appropriate department.",
     "Services", True),
    ("Predictive Traffic Management Analytics Platform",
     "Machine learning based predictive analytics system to forecast traffic congestion "
     "using historical and real-time sensor data.",
     "Services", True),
    ("Smart City Integrated Command and Control Platform",
     "Establishment of an integrated command and control centre with dashboards for "
     "municipal services monitoring.",
     "Works", False),
    ("Generative AI Assistant for Legal Document Drafting",
     "Deployment of a generative AI / LLM based assistant to help draft and review "
     "standard legal notices and RTI responses.",
     "Services", True),
    ("Computer Vision Based Crop Health Monitoring System",
     "AI/ML computer vision system to analyze drone and satellite imagery for early "
     "detection of crop disease and yield estimation.",
     "Goods & Services", True),
    ("Automated Welfare Eligibility Screening System",
     "Machine learning based automated decision system to assess applicant eligibility "
     "for state welfare and pension schemes.",
     "Services", True),
    ("Office Furniture Procurement for District Collectorate",
     "Supply of office furniture including chairs, desks and cabinets for the district "
     "collectorate building.",
     "Goods", False),
    ("Intelligent Surveillance System for Metro Rail Security",
     "Deployment of an intelligent video analytics and object detection surveillance "
     "system across metro rail stations for security monitoring.",
     "Goods & Services", True),
    ("Road Resurfacing Works - District Highway 42",
     "Resurfacing and pothole repair works for a 12 km stretch of district highway.",
     "Works", False),
    ("AI-Powered Healthcare Prioritization and Triage System",
     "Predictive analytics platform to prioritize patients in government hospital "
     "emergency departments based on risk scoring.",
     "Services", True),
    ("Biometric Identification System for Ration Card Verification",
     "Supply and integration of biometric identification hardware and matching software "
     "for public distribution system beneficiary verification.",
     "Goods & Services", True),
    ("Recruitment Screening AI Tool for Government Hiring Portal",
     "Automated resume screening and candidate ranking tool using natural language "
     "processing for state government recruitment drives.",
     "Services", True),
    ("Document Summarization Tool for Internal Departmental Use",
     "Internal-use generative AI tool to summarize lengthy departmental correspondence "
     "and meeting minutes for staff reference.",
     "Services", True),
    ("Speech Recognition Based Multilingual IVR for Helpline",
     "AI speech recognition and NLP based interactive voice response system supporting "
     "regional languages for a state helpline.",
     "Services", True),
]

# Extra bulk of clearly non-AI tenders to make the discovery filter meaningful
BULK_NON_AI_TITLES = [
    "Supply of Stationery Items for District Office",
    "Construction of Community Health Centre Building",
    "Annual Maintenance Contract for Water Pumps",
    "Procurement of School Textbooks for Government Schools",
    "Renovation of Municipal Park",
    "Supply of Medical Equipment for Primary Health Centre",
    "Streetlight Installation Project Phase 2",
    "Catering Services for State Government Guest House",
]


def build_raw_dataset(n_bulk: int = 4900) -> pd.DataFrame:
    rows = []
    tid = 1

    for title, desc, ttype, _ in RAW_TENDER_TEMPLATES:
        org = random.choice(ORGS)
        state = random.choice(STATES)
        rows.append({
            "tender_id": f"TND-{tid:06d}",
            "organisation": org,
            "state": state,
            "title": title,
            "tender_description": desc,
            "tender_type": ttype,
            "date": "2026-04-15",
            "contract_value": random.choice([2500000, 8500000, 15000000, 42000000]),
            "selected_bidder": "TBD",
            "detail_url": f"https://example-tenders.gov.in/tender/{tid}",
            "tender_document_url": f"https://example-tenders.gov.in/docs/{tid}.pdf",
        })
        tid += 1

    for i in range(n_bulk):
        title = random.choice(BULK_NON_AI_TITLES)
        org = random.choice(ORGS)
        state = random.choice(STATES)
        rows.append({
            "tender_id": f"TND-{tid:06d}",
            "organisation": org,
            "state": state,
            "title": f"{title} - Package {i % 37 + 1}",
            "tender_description": f"Routine procurement under {org}, {state}.",
            "tender_type": random.choice(["Goods", "Works", "Services"]),
            "date": "2026-03-01",
            "contract_value": random.choice([150000, 500000, 1200000]),
            "selected_bidder": "TBD",
            "detail_url": f"https://example-tenders.gov.in/tender/{tid}",
            "tender_document_url": f"https://example-tenders.gov.in/docs/{tid}.pdf",
        })
        tid += 1

    return pd.DataFrame(rows)


def build_governance_findings(tender_id: str, ai_type: str) -> dict[str, GovernanceFinding]:
    """Synthesize plausible, varied governance findings for demo purposes."""
    findings = {}

    # Data categories - almost always something is documented
    data_map = {
        "Facial Recognition": "Facial images + CCTV video",
        "Biometric Identification": "Biometric data + identity records",
        "Conversational AI": "Citizen grievance text + contact details",
        "Computer Vision": "Video feeds + object metadata",
        "Predictive Analytics": "Historical traffic sensor data",
        "Generative AI / LLM": "Departmental documents (non-personal)",
        "NLP": "Call transcripts + citizen queries",
        "AI / Machine Learning": "Applicant records + eligibility data",
    }
    summary = data_map.get(ai_type, "Operational data relevant to the AI system")
    findings["data_categories"] = GovernanceFinding(
        tender_id=tender_id, dimension="data_categories", verdict=Verdict.FOUND,
        summary=summary,
        evidence=[Evidence(snippet=f"The system shall process {summary.lower()} as specified in Annexure B.",
                            clause="4.2", page=random.randint(10, 25), source_document="tender_document.pdf")],
    )

    # Human oversight - vary outcomes for demo realism
    oversight_roll = random.random()
    if oversight_roll < 0.35:
        findings["human_oversight"] = GovernanceFinding(
            tender_id=tender_id, dimension="human_oversight", verdict=Verdict.REQUIRED,
            summary="Human review required before action",
            evidence=[Evidence(snippet="Human review shall be conducted before any flagged output is acted upon.",
                                clause="8.3", page=random.randint(30, 55), source_document="tender_document.pdf")],
        )
    elif oversight_roll < 0.6:
        findings["human_oversight"] = GovernanceFinding(
            tender_id=tender_id, dimension="human_oversight", verdict=Verdict.UNCLEAR,
            summary="Human involvement mentioned, role unclear",
            evidence=[Evidence(snippet="An authorized official may review system outputs as deemed necessary.",
                                clause="6.1", page=random.randint(20, 40), source_document="tender_document.pdf")],
        )
    else:
        findings["human_oversight"] = GovernanceFinding(
            tender_id=tender_id, dimension="human_oversight", verdict=Verdict.NOT_FOUND,
            summary=config.NOT_FOUND_MESSAGE,
        )

    # Bias/fairness testing - mostly NOT_FOUND, matching the pitch's central example
    if random.random() < 0.2:
        findings["bias_fairness_testing"] = GovernanceFinding(
            tender_id=tender_id, dimension="bias_fairness_testing", verdict=Verdict.FOUND,
            summary="Accuracy testing across demographic groups required",
            evidence=[Evidence(snippet="Vendor shall demonstrate system accuracy across age, gender and skin-tone groups.",
                                clause="9.4", page=random.randint(40, 60), source_document="tender_document.pdf")],
        )
    else:
        findings["bias_fairness_testing"] = GovernanceFinding(
            tender_id=tender_id, dimension="bias_fairness_testing", verdict=Verdict.NOT_FOUND,
            summary=config.NOT_FOUND_MESSAGE,
        )

    # Failure & fallback
    if random.random() < 0.55:
        findings["failure_fallback"] = GovernanceFinding(
            tender_id=tender_id, dimension="failure_fallback", verdict=Verdict.FOUND,
            summary="Manual fallback and human override documented",
            evidence=[Evidence(snippet="In the event of system malfunction, operations shall revert to the manual process.",
                                clause="11.2", page=random.randint(45, 70), source_document="tender_document.pdf")],
        )
    else:
        findings["failure_fallback"] = GovernanceFinding(
            tender_id=tender_id, dimension="failure_fallback", verdict=Verdict.NOT_FOUND,
            summary=config.NOT_FOUND_MESSAGE,
        )

    return findings


def main():
    print("Building synthetic raw tender dataset...")
    raw_df = build_raw_dataset()
    raw_df.to_parquet(config.RAW_TENDERS_PARQUET, index=False)
    print(f"  -> {len(raw_df)} rows written to {config.RAW_TENDERS_PARQUET}")

    print("Running Stage 1 keyword discovery...")
    candidates = filter_candidates(raw_df)
    candidates.to_parquet(config.CANDIDATES_PARQUET, index=False)
    print(f"  -> {len(candidates)} AI candidates identified")

    print("Capability map preview:")
    print(capability_map(candidates).to_string(index=False))

    print("\nSeeding confirmed tenders + governance evidence into SQLite (simulating a full pipeline run)...")
    db.init_db(config.SQLITE_DB_PATH)

    confirmed_seed = [row for _, row in candidates.iterrows() if row["title"] in
                      [t[0] for t in RAW_TENDER_TEMPLATES if t[3]]]

    ai_type_lookup = {t[0]: (t[1]) for t in RAW_TENDER_TEMPLATES}
    ai_type_label_lookup = {
        "AI-Based Facial Recognition System for Public Surveillance": "Facial Recognition",
        "Chatbot for Citizen Grievance Redressal": "Conversational AI",
        "Predictive Traffic Management Analytics Platform": "Predictive Analytics",
        "Generative AI Assistant for Legal Document Drafting": "Generative AI / LLM",
        "Computer Vision Based Crop Health Monitoring System": "Computer Vision",
        "Automated Welfare Eligibility Screening System": "AI / Machine Learning",
        "Intelligent Surveillance System for Metro Rail Security": "Computer Vision",
        "AI-Powered Healthcare Prioritization and Triage System": "Predictive Analytics",
        "Biometric Identification System for Ration Card Verification": "Biometric Identification",
        "Recruitment Screening AI Tool for Government Hiring Portal": "AI / Machine Learning",
        "Document Summarization Tool for Internal Departmental Use": "Generative AI / LLM",
        "Speech Recognition Based Multilingual IVR for Helpline": "NLP",
    }

    count = 0
    for row in confirmed_seed:
        title = row["title"]
        ai_type = ai_type_label_lookup.get(title, "AI / Machine Learning")
        tender = ConfirmedAITender(
            tender_id=row["tender_id"],
            organisation=row["organisation"],
            state=row["state"],
            title=title,
            ai_type=ai_type,
            confidence="high",
            verification_reasoning=(
                f"Title and description explicitly describe {ai_type.lower()} functionality "
                "beyond a generic keyword mention."
            ),
            is_priority=True,
        )
        impact_level, impact_reasoning = classify_impact(ai_type, title, row["tender_description"])
        db.upsert_confirmed_tender(config.SQLITE_DB_PATH, tender, impact_level=impact_level,
                                    impact_reasoning=impact_reasoning)

        findings = build_governance_findings(tender.tender_id, ai_type)
        for finding in findings.values():
            db.save_finding(config.SQLITE_DB_PATH, finding)
        count += 1

    print(f"  -> {count} confirmed AI tenders with governance evidence written to {config.SQLITE_DB_PATH}")
    print("\nDone. Run: streamlit run app/streamlit_app.py")


if __name__ == "__main__":
    main()
