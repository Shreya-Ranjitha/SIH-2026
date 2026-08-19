"""Unit tests for Stage 1 keyword discovery.

Run with: pytest tests/
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.discovery.keywords import is_candidate, primary_ai_types, scan_text


def test_facial_recognition_matches():
    assert is_candidate("AI-Based Facial Recognition System", "Uses facial recognition for surveillance")


def test_generic_smart_city_title_may_not_match():
    # Title alone shouldn't false-positive on "smart" or "city"
    assert not is_candidate("Smart City Integrated Command Centre", "Dashboards for municipal services monitoring")


def test_hidden_ai_in_description_matches():
    # Title looks generic, but description reveals real AI content
    assert is_candidate(
        "Intelligent Surveillance System",
        "The system shall include computer vision and facial recognition capability.",
    )


def test_non_ai_tender_does_not_match():
    assert not is_candidate("Supply of Office Furniture", "Chairs, desks and cabinets for district office")


def test_primary_ai_types_deduplicates():
    types = primary_ai_types("AI AI AI Chatbot", "machine learning machine learning conversational ai")
    assert len(types) == len(set(types))


def test_scan_text_empty_input():
    result = scan_text("")
    assert not result.matched
    assert result.ai_types == []


def test_scan_text_case_insensitive():
    result = scan_text("This tender involves ARTIFICIAL INTELLIGENCE components.")
    assert result.matched
