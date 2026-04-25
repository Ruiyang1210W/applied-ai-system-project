"""
Automated tests for the RAG advisory pipeline.

Groups:
  1. Retriever  — does retrieve() return sensible docs?
  2. Guardrails — does validate_suggestions() catch bad output?
  3. End-to-end — does suggest_tasks() work correctly? (Claude call is mocked)

Run with: python -m pytest tests/test_rag.py -v
"""
from unittest.mock import patch

import pytest

from pawpal_system import Pet
from pet_knowledge_base import get_age_group, retrieve
from rag_advisor import MAX_SUGGESTIONS, suggest_tasks, validate_suggestions

# ---------------------------------------------------------------------------
# 1. Retriever tests
# ---------------------------------------------------------------------------

def test_retrieve_dog_adult_returns_results():
    docs = retrieve("dog", 4, "")
    assert len(docs) > 0

def test_retrieve_cat_senior_contains_senior_guidance():
    docs = retrieve("cat", 12, "")
    combined = " ".join(docs).lower()
    assert "senior" in combined or "11+" in combined

def test_retrieve_unknown_species_falls_back_to_general():
    docs = retrieve("hamster", 2, "")
    assert len(docs) > 0

def test_retrieve_hip_note_adds_condition_docs():
    docs_with    = retrieve("dog", 4, "has a bad hip")
    docs_without = retrieve("dog", 4, "")
    assert len(docs_with) > len(docs_without)

def test_retrieve_diabetic_note_adds_insulin_guidance():
    docs = retrieve("cat", 13, "diabetic")
    combined = " ".join(docs).lower()
    assert "insulin" in combined or "diabetic" in combined

def test_age_group_dog_boundaries():
    assert get_age_group("dog", 0) == "puppy"
    assert get_age_group("dog", 3) == "adult"
    assert get_age_group("dog", 8) == "senior"

def test_age_group_cat_boundaries():
    assert get_age_group("cat", 0) == "kitten"
    assert get_age_group("cat", 5) == "adult"
    assert get_age_group("cat", 12) == "senior"

# ---------------------------------------------------------------------------
# 2. Guardrail / validation tests
# ---------------------------------------------------------------------------

GOOD = {
    "name": "Morning walk",
    "duration_minutes": 20,
    "priority": "high",
    "category": "walk",
    "frequency": "daily",
    "confidence": 0.9,
}

def test_validate_accepts_valid_task():
    assert len(validate_suggestions([GOOD])) == 1

def test_validate_rejects_zero_duration():
    assert len(validate_suggestions([{**GOOD, "duration_minutes": 0}])) == 0

def test_validate_rejects_negative_duration():
    assert len(validate_suggestions([{**GOOD, "duration_minutes": -5}])) == 0

def test_validate_rejects_invalid_priority():
    assert len(validate_suggestions([{**GOOD, "priority": "urgent"}])) == 0

def test_validate_caps_at_max_suggestions():
    many = [{**GOOD, "name": f"Task {i}"} for i in range(20)]
    assert len(validate_suggestions(many)) == MAX_SUGGESTIONS

def test_validate_clamps_confidence_above_one():
    result = validate_suggestions([{**GOOD, "confidence": 1.5}])
    assert result[0]["confidence"] == 1.0

def test_validate_clamps_confidence_below_zero():
    result = validate_suggestions([{**GOOD, "confidence": -0.3}])
    assert result[0]["confidence"] == 0.0

def test_validate_rejects_duration_above_max():
    assert len(validate_suggestions([{**GOOD, "duration_minutes": 300}])) == 0

# ---------------------------------------------------------------------------
# 3. suggest_tasks end-to-end (Claude call mocked)
# ---------------------------------------------------------------------------

MOCK_SUGGESTIONS = [
    {
        "name": "Morning walk",
        "duration_minutes": 20,
        "priority": "high",
        "category": "walk",
        "frequency": "daily",
        "confidence": 0.95,
    },
    {
        "name": "Evening feeding",
        "duration_minutes": 10,
        "priority": "high",
        "category": "feeding",
        "frequency": "daily",
        "confidence": 0.98,
    },
]

def test_suggest_tasks_returns_list_on_success():
    pet = Pet(name="Luna", species="dog", age=4, notes="")
    with patch("rag_advisor.call_claude", return_value=MOCK_SUGGESTIONS):
        result = suggest_tasks(pet)
    assert isinstance(result, list)
    assert len(result) == 2

def test_suggest_tasks_all_confidence_in_range():
    pet = Pet(name="Luna", species="dog", age=4, notes="")
    with patch("rag_advisor.call_claude", return_value=MOCK_SUGGESTIONS):
        result = suggest_tasks(pet)
    for task in result:
        assert 0.0 <= task["confidence"] <= 1.0

def test_suggest_tasks_returns_empty_on_api_failure():
    pet = Pet(name="Luna", species="dog", age=4, notes="")
    with patch("rag_advisor.call_claude", side_effect=Exception("connection error")):
        result = suggest_tasks(pet)
    assert result == []

def test_suggest_tasks_filters_invalid_suggestions_from_api():
    bad_then_good = [
        {**MOCK_SUGGESTIONS[0], "duration_minutes": 0},  # invalid — should be dropped
        MOCK_SUGGESTIONS[1],                              # valid
    ]
    pet = Pet(name="Luna", species="dog", age=4, notes="")
    with patch("rag_advisor.call_claude", return_value=bad_then_good):
        result = suggest_tasks(pet)
    assert len(result) == 1
    assert result[0]["name"] == "Evening feeding"
