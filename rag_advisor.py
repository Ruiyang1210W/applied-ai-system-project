"""
RAG advisor: retrieves pet care guidelines and asks Claude to suggest tasks.

Main entry point:
    suggest_tasks(pet) -> list[dict]

Each returned dict has keys:
    name, duration_minutes, priority, category, frequency, confidence

Returns [] on any API or parse failure so the app always degrades gracefully.
"""
from __future__ import annotations

import json
import logging
import os

from dotenv import load_dotenv
from pawpal_system import Pet
from pet_knowledge_base import retrieve

load_dotenv()

# ---------------------------------------------------------------------------
# Logging — every retrieval, prompt, response, and user decision is recorded.
# ---------------------------------------------------------------------------
logging.basicConfig(
    filename="pawpal_rag.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Guardrail constants
# ---------------------------------------------------------------------------
MAX_SUGGESTIONS = 8
MIN_DURATION    = 1
MAX_DURATION    = 240
VALID_PRIORITIES  = {"high", "medium", "low"}
VALID_FREQUENCIES = {"daily", "weekly", "as-needed"}


# ---------------------------------------------------------------------------
# Guardrails: validate Claude's output before it touches the scheduler
# ---------------------------------------------------------------------------
def validate_suggestions(suggestions: list[dict]) -> list[dict]:
    """
    Remove suggestions that fail sanity checks and cap at MAX_SUGGESTIONS.
    Clamps the confidence score to [0.0, 1.0].
    """
    valid = []
    for s in suggestions:
        name = s.get("name", "<unnamed>")
        dur  = s.get("duration_minutes", 0)
        pri  = s.get("priority", "")

        if not isinstance(dur, (int, float)) or dur < MIN_DURATION:
            log.warning("Rejected '%s': duration_minutes=%s is too short", name, dur)
            continue
        if dur > MAX_DURATION:
            log.warning("Rejected '%s': duration_minutes=%s exceeds max", name, dur)
            continue
        if pri not in VALID_PRIORITIES:
            log.warning("Rejected '%s': priority=%r is not valid", name, pri)
            continue

        s["confidence"] = max(0.0, min(1.0, float(s.get("confidence", 0.5))))
        valid.append(s)

    if len(valid) > MAX_SUGGESTIONS:
        log.info("Capped suggestions from %d to %d", len(valid), MAX_SUGGESTIONS)

    return valid[:MAX_SUGGESTIONS]


# ---------------------------------------------------------------------------
# Claude call — isolated as its own function so tests can mock it cleanly
# ---------------------------------------------------------------------------
def call_claude(prompt: str) -> list[dict]:
    """
    Send prompt to Gemini and return the parsed JSON list.
    Raises on any API or parse failure.
    """
    from google import genai

    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    raw = response.text
    log.info("Gemini response length: %d chars", len(raw))

    start = raw.find("[")
    end   = raw.rfind("]") + 1
    if start == -1 or end == 0:
        raise ValueError(f"No JSON array in Claude response: {raw[:200]!r}")

    return json.loads(raw[start:end])


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------
def _build_prompt(pet: Pet, guidelines: list[str]) -> str:
    guidelines_block = "\n".join(f"- {g}" for g in guidelines)
    return f"""You are a pet care advisor. Based ONLY on the care guidelines below, suggest 4-6 daily care tasks for this specific pet.

PET PROFILE:
- Name: {pet.name}
- Species: {pet.species}
- Age: {pet.age} years
- Notes: {pet.notes or "none"}

CARE GUIDELINES (retrieved for this pet):
{guidelines_block}

Return ONLY a valid JSON array. Each element must have exactly these fields:
- "name": short, clear task name (string)
- "duration_minutes": realistic time in minutes (integer, 1-240)
- "priority": exactly one of "high", "medium", "low"
- "category": exactly one of "walk", "feeding", "meds", "grooming", "enrichment", "other"
- "frequency": exactly one of "daily", "weekly", "as-needed"
- "confidence": how strongly the retrieved guidelines support this task (float, 0.0-1.0)

No explanation, no markdown fences, only the JSON array."""


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
def suggest_tasks(pet: Pet) -> list[dict]:
    """
    Retrieve care guidelines for the pet, ask Claude to generate task suggestions,
    validate the output, and return the cleaned list.

    Returns [] on any failure so the app always degrades gracefully.
    """
    log.info("suggest_tasks | %s | %s | age=%s | notes=%r",
             pet.name, pet.species, pet.age, pet.notes)

    guidelines = retrieve(pet.species, pet.age, pet.notes)
    log.info("Retrieved %d guidelines", len(guidelines))

    prompt = _build_prompt(pet, guidelines)
    log.info("Prompt length: %d chars", len(prompt))

    try:
        raw = call_claude(prompt)
        log.info("Claude returned %d raw suggestions", len(raw))

        validated = validate_suggestions(raw)
        log.info("Validated %d suggestions", len(validated))

        if validated:
            avg_conf = sum(s["confidence"] for s in validated) / len(validated)
            log.info("Average confidence score: %.2f", avg_conf)

        return validated

    except Exception as exc:
        log.error("suggest_tasks failed: %s", exc)
        return []
