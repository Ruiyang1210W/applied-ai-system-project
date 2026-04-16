# PawPal+ — AI-Powered Pet Care Scheduler

## Original Project (Modules 1–3)

PawPal+ was originally built in Module 2 as a pure-Python scheduling tool for busy pet owners. Its goal was to take a list of care tasks across multiple pets, sort them by priority, and fit them into a daily time budget — producing a time-slotted schedule with start times and conflict warnings. The system had no AI component: the owner manually entered every task by hand, relying entirely on their own knowledge of what their pet needed.

---

## Title and Summary

**PawPal+** is a daily pet care planner that combines AI-generated task suggestions with a priority-based scheduler, so pet owners spend less time figuring out *what* to do and more time actually doing it.

Most pet care apps make you build your routine from scratch. New pet owners often don't know what tasks to include, how often, or how long they take. PawPal+ solves this by using Retrieval-Augmented Generation (RAG): when you add a pet, the app looks up species- and age-specific care guidelines from a curated knowledge base, then uses Claude to turn those guidelines into a concrete, personalized task list. You review and approve each suggestion before it enters your schedule — so the AI assists without overriding your judgment.

---

## Architecture Overview

The system has two layers that work together:

**Core scheduling layer** (`pawpal_system.py`) — four Python classes handle all the non-AI logic. `CareTask` stores one activity with its duration, priority, and frequency. `Pet` owns a task list and handles recurring task creation. `Owner` holds all pets and aggregates their tasks. `Scheduler` fits tasks into the owner's time budget, assigns `HH:MM` start times, detects time-window conflicts, and supports filtering by pet or status.

**RAG advisory layer** (`pet_knowledge_base.py` + `rag_advisor.py`) — when you add a pet, a retriever filters a local knowledge base of care guidelines by species, age group (puppy/adult/senior), and any keywords in the pet's notes (e.g. "bad hip", "diabetic"). The matched guidelines, along with the pet's profile, are sent to Claude in a structured prompt. Claude returns a JSON list of task suggestions. Those suggestions appear in the Streamlit UI for human review: you accept, edit, or skip each one individually. Only approved tasks enter the scheduler.

Every retrieval query, LLM prompt, and user decision is written to `pawpal_rag.log`. Guardrails validate that returned tasks have sensible durations and cap the number of suggestions per call, so an API error or bad response never corrupts the schedule.

Full diagrams:
- Class diagram: [`design/class_diagram.mmd`](design/class_diagram.mmd)
- System diagram: [`design/system_diagram.mmd`](design/system_diagram.mmd)

---

## Setup Instructions

**Requirements:** Python 3.10+, an Anthropic API key.

### 1. Clone the repo

```bash
git clone https://github.com/your-username/applied-ai-system-project.git
cd applied-ai-system-project
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Set your API key

```bash
# macOS / Linux
export ANTHROPIC_API_KEY="sk-ant-..."

# Windows (PowerShell)
$env:ANTHROPIC_API_KEY="sk-ant-..."
```

### 4. Run the app

```bash
python -m streamlit run app.py
```

Opens at `http://localhost:8501`.

### 5. Run the tests

```bash
python -m pytest tests/ -v
```

---

## Sample Interactions

These examples show the RAG pipeline in action — what you enter, what the system retrieves, and what Claude suggests.

### Example 1 — Adult dog with a health note

**User input:**
- Pet name: Luna
- Species: dog
- Age: 4 years
- Notes: "has a bad hip"

**Retrieved guidelines (from knowledge base):**
> Adult dogs need 30–60 min of exercise daily. Dogs with joint issues should avoid high-impact activity; low-impact walks and swimming are preferred. Dental hygiene: daily chew or brush. Feeding: twice daily. Monthly flea/tick/heartworm prevention.

**Claude's task suggestions:**
```
1. Morning walk (low impact)  — 20 min, high priority, daily
2. Evening walk (short)       — 15 min, medium priority, daily
3. Morning feeding            — 10 min, high priority, daily
4. Evening feeding            — 10 min, high priority, daily
5. Dental chew                —  5 min, medium priority, daily
6. Flea & tick prevention     —  5 min, high priority, monthly (as-needed)
```

**User action:** Accepts all except "Evening walk (short)" — edits it down to 10 min before accepting.

---

### Example 2 — Senior cat

**User input:**
- Pet name: Mochi
- Species: cat
- Age: 13 years
- Notes: "indoor only, diabetic"

**Retrieved guidelines (from knowledge base):**
> Senior cats (11+) need twice-daily feeding on a consistent schedule. Diabetic cats require insulin injections timed with meals; monitor for lethargy or vomiting. Litter box should be scooped daily. Enrichment is important but should be low-stress (puzzle feeders, gentle play). Annual bloodwork recommended.

**Claude's task suggestions:**
```
1. Morning feeding + insulin   — 10 min, high priority, daily
2. Evening feeding + insulin   — 10 min, high priority, daily
3. Litter box scoop            —  5 min, high priority, daily
4. Gentle play / enrichment    — 10 min, medium priority, daily
5. Health check (weight, mood) —  5 min, medium priority, daily
```

**User action:** Accepts all. Generates schedule — all 5 tasks fit within 60 min available time.

---

### Example 3 — Young rabbit, no API key (fallback)

**User input:**
- Pet name: Biscuit
- Species: rabbit
- Age: 1 year
- Notes: ""

**What happens when the API call fails:**
The app logs the error to `pawpal_rag.log`, shows an inline warning ("Could not reach Claude — showing knowledge base summary instead"), and displays the raw retrieved guidelines so the user can still add tasks manually.

```
[WARN] Claude API call failed: connection timeout.
[INFO] Fallback: displaying retrieved guidelines for rabbit/adult.
Retrieved: Rabbits need unlimited hay, fresh leafy greens daily, and at least
2 hours of exercise outside their enclosure. Litter box cleaning daily.
Nail trims every 6–8 weeks.
```

---

## Design Decisions

**Why RAG instead of a fine-tuned model or pure prompting?**
A fine-tuned model would require labeled training data we don't have. Pure prompting (no retrieval) works but produces generic advice that ignores the pet's specific age, species, or health notes. RAG lets us keep a small, auditable knowledge base that a vet or domain expert could review and update, while still letting Claude handle language generation. The retrieval step is what makes the advice specific rather than generic.

**Why human review before tasks enter the scheduler?**
AI suggestions are a starting point, not gospel. A 4-hour "deep grooming" suggestion for a 15-minute time budget would break the schedule. Requiring explicit user approval on each task keeps the owner in control and makes it obvious when a suggestion is unrealistic.

**Why a local knowledge base instead of web search?**
Web search introduces latency, rate limits, and unpredictable content. A curated local knowledge base is fast, offline-capable, and consistent — important for a daily-use tool. The trade-off is that it needs manual updates when care guidelines change.

**Why greedy scheduling instead of optimal knapsack?**
The greedy algorithm (sort by priority, fit tasks one at a time) is predictable: owners can look at the priority list and understand exactly why the plan came out the way it did. A knapsack solver would occasionally produce a "better" schedule but would be harder to explain and unnecessary for 5–15 daily tasks.

**Conflict detection is O(n²) — intentionally.**
Comparing every task pair is fine at this scale (5–15 tasks). A sorted interval sweep would be faster but harder to read. The current approach keeps the logic auditable.

---

## Testing Summary

**What was tested (37 unit tests in `tests/test_pawpal.py`):**
- Tasks fitting (and not fitting) into the time budget, including exact-fit edge cases
- Priority sort order — high before medium before low regardless of insertion order
- Recurring task creation — daily creates a new task due tomorrow, weekly in 7 days, as-needed creates nothing
- Conflict detection — overlapping windows flagged, back-to-back windows correctly not flagged
- Filtering — by pet name and by done/pending status
- Edge cases — owner with no pets, pet with no tasks, zero minutes available, completing the same task twice

**What worked:** The core scheduler logic is solid. All 37 tests pass. The greedy algorithm produces correct results for all tested inputs, and conflict detection catches every overlapping pair without false positives.

**What didn't:** No automated tests yet for the RAG pipeline — testing LLM outputs is inherently harder because responses vary. This is an honest gap.

**What I'd test next:** Response consistency (does Claude suggest the same tasks for the same input across multiple calls?), and the fallback path when the API is unavailable.

---

## Reflection

The biggest thing this project taught me is that AI is genuinely useful as a *retrieval + generation* system, not just a chatbot. Without RAG, Claude would give the same generic "walk your dog daily" advice to every dog regardless of age or health. Adding a retrieval step — even a simple keyword filter over a local file — immediately makes the output more specific and trustworthy.

The human review step was a deliberate design choice I'm glad I made. It would have been simpler to auto-add every suggestion to the schedule, but that would have made the AI invisible and unaccountable. Requiring approval means the user sees what was retrieved, why Claude suggested it, and has one chance to catch anything wrong. That's the right model for an assistant: it does the research, you make the call.

On the engineering side: structured outputs (asking Claude to return JSON with specific fields) matter a lot. Free-text responses are hard to parse reliably. Defining the output schema upfront — name, duration, priority, category, frequency — and validating it before it touches the scheduler is what keeps the AI layer from breaking the rest of the app.
