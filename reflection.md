# PawPal+ Project Reflection

## 2. System Architecture (RAG Design)

**System diagram:** [`design/system_diagram.mmd`](design/system_diagram.mmd)

### Components and their roles

| Component | File | What it does |
|---|---|---|
| **Pet Knowledge Base** | `pet_knowledge_base.py` | Static library of care guidelines organized by species, age group, and condition keywords. The source of ground-truth that the AI retrieves from. |
| **Retriever** | `rag_advisor.py` | Filters the knowledge base using the pet's species, age group (puppy/adult/senior), and any keywords from the notes field. Returns the most relevant guidelines as plain text. |
| **Claude API (LLM)** | `rag_advisor.py` | Receives the pet profile + retrieved docs in a structured prompt and returns a JSON list of task suggestions. This is the RAG step — the model's answer is grounded in retrieved context, not just training data. |
| **Human Review UI** | `app.py` | Streamlit interface where the user sees each AI-suggested task and individually accepts, edits, or skips it before anything enters the scheduler. |
| **PawPal Core** | `pawpal_system.py` | Existing `Pet`, `Owner`, `Scheduler` classes. Accepted tasks are added via `pet.add_task()` and flow into the existing scheduling pipeline unchanged. |
| **Logger / Guardrails** | `rag_advisor.py` | Logs every retrieval query, prompt sent, response received, and user accept/reject decision to `pawpal_rag.log`. Guardrails cap task count, validate duration bounds, and provide a fallback if the API call fails. |

### Data flow (input → process → output)

```
User enters pet (species, age, notes)
    → Retriever filters Pet Knowledge Base → relevant care docs
    → Claude API receives [pet profile + retrieved docs] → JSON task suggestions
    → Streamlit UI shows suggestions → Human accepts / edits / skips each
    → Accepted tasks → Pet.add_task() → Scheduler.generate_plan()
    → Daily schedule with times, priorities, and conflict warnings
```

### Where humans check AI output

The human review step sits between the LLM response and any change to the schedule. No AI-suggested task enters the system without explicit user approval. This means:
- The AI cannot silently add a bad suggestion (e.g., a 4-hour task for a 5-minute bird)
- The user sees the reasoning (retrieved guidelines are shown alongside suggestions)
- The logger captures every accept/reject decision for auditability

---

## 1. System Design

**a. Initial design**

The app is built around three things a user actually needs to do:

1. **Set up their profile and pet info** — The user enters their name, their pet's name and type, and how much free time they have in a day. This is the starting point because the schedule has to fit around the owner's real availability.

2. **Add and manage care tasks** — The user can add tasks like walks, feeding, giving meds, or grooming. Each task has a name, how long it takes, and how important it is. They can also edit or remove tasks as things change.

3. **Generate and read the daily plan** — Once the tasks are in, the user can generate a schedule. The app figures out what fits in the day and puts it in a reasonable order based on priority and time. It also gives a short reason for why the plan looks the way it does.

These three steps follow a simple flow: you describe yourself and your pet, you list what needs to get done, and then the app helps you figure out when to do it.

**b. Design changes**

After reviewing the skeleton, a few things got changed before writing any real logic:

1. **Added `set_pet()` to `Owner`** — The original design left `owner.pet` as a plain attribute with no setter. That meant the only way to assign a pet was to reach directly into the object from outside. Adding `set_pet()` keeps it consistent with how `add_task()` works and makes the intent clearer.

2. **`generate_plan()` now returns `List[CareTask]`** — It used to return `None`, which made the flow confusing. You'd call `generate_plan()`, then separately call `get_plan()` to get anything back. Now `generate_plan()` populates the internal lists *and* returns the result directly. `get_plan()` stays as a simple getter for the cached result if you need it later.

3. **`get_tasks()` now returns `self.tasks` explicitly** — It had `pass` before, which means it would have returned `None`. Since `Scheduler` depends on this method to build the plan, a silent `None` return would have caused hard-to-debug crashes. Fixed it in the stub so there's no ambiguity.

4. **`CareTask.edit()` now covers all four fields** — The original only allowed editing `duration_minutes` and `priority`. Since the UI will let users update tasks, `name` and `category` need to be editable too.

5. **Added priority validation via `__post_init__`** — `priority` is a free string with no guardrails. Added a `VALID_PRIORITIES` constant and a `__post_init__` check that raises a `ValueError` for anything outside `"high"`, `"medium"`, `"low"`. This catches bad input early before it reaches the scheduler.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
Time, priority
- How did you decide which constraints mattered most?
Depends on the priority

**b. Tradeoffs**

The scheduler uses a **greedy algorithm**: it sorts tasks by priority, then fits them into the available time budget one at a time. Once a task claims a slot, the decision is final — the scheduler never goes back to reconsider.

This means a single long high-priority task (say, a 60-minute vet visit) can consume so much time that several shorter medium-priority tasks all get skipped, even though dropping the long task would have fit three of them instead.

A smarter approach would be a proper knapsack algorithm that tries multiple combinations and picks the one with the highest total priority value. That would produce a better plan in edge cases.

The greedy approach is kept for two reasons:
1. It's predictable — a pet owner can look at the priority list and understand exactly why the plan came out the way it did.
2. For typical daily care (walks, feeding, meds), task counts are small and the greedy result is almost always good enough. The complexity of a full knapsack solver isn't worth it here.

A second, smaller tradeoff: conflict detection runs in O(n²) time by comparing every pair of tasks. For 6–10 daily tasks this is instant, but it would slow down noticeably with very large task lists. A sorted interval sweep would be faster, but harder to read and unnecessary at this scale.

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
Design brainstorming and debugging
- What kinds of prompts or questions were most helpful?
The more specific prompts the more helpful.

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
The UML diagram part
- How did you evaluate or verify what the AI suggested?
I verify the diagram on https://mermaid.live/ to check if they are all correct.
---

## 4. Testing and Verification

### Scheduler tests (`tests/test_pawpal.py`) — 37 tests

Covers: time budget fitting, priority sort order, recurring task creation (daily/weekly/as-needed), conflict detection, filtering by pet and status, and edge cases (no pets, no tasks, zero minutes, completing the same task twice).

**Result:** 37/37 passed. Confidence: 4/5 — core logic is solid; conflict checker is O(n²) which is fine at daily pet-care scale.

---

### RAG pipeline tests (`tests/test_rag.py`) — 19 tests, 3 groups

**Group 1 — Retriever (7 tests)**
Tests that `retrieve()` returns the right guidelines for each species, that unknown species fall back to general guidance, that condition-flag keywords (hip, diabetic) add the correct extra docs, and that age group boundaries map correctly.

**Group 2 — Guardrails / Validation (8 tests)**
Tests that `validate_suggestions()` rejects zero, negative, and over-max durations; rejects invalid priority values; caps output at `MAX_SUGGESTIONS`; and clamps confidence scores to [0.0, 1.0].

**Group 3 — End-to-end with mocked Claude (4 tests)**
Tests the full `suggest_tasks()` flow without hitting the real API. Verifies that a successful mock call returns the expected list, all confidence values are in range, an API failure returns `[]` instead of crashing, and invalid items in the mock response are filtered out before being returned.

**Result:** 19/19 passed in 0.11s. **Total: 56/56 tests passing.**

**Testing summary:** The RAG pipeline tests don't require a live API key — the Claude call is mocked so they run offline and deterministically. One honest gap: there are no tests for response consistency across real API calls (does Claude suggest the same tasks on every run?). That would require a live key and a separate evaluation script.

**What I learned:** Isolating `call_claude()` as its own function made mocking trivial and kept tests fast. Validating AI output with explicit bounds (duration, priority, confidence clamp) before it touches the scheduler is what prevents a bad API response from corrupting the user's data.

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?
When the project is ready for use and can be helpful for people

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?
I'd rework how the scheduler handles time. Right now it just stacks tasks back-to-back starting at 08:00.

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
AI is really good at filling in code fast but it doesn't know what you actually want. The most useful moments were when I reviewed what it suggested and pushed back on it.