# PawPal+ (Module 2 Project)

PawPal+ is a Streamlit app that helps a busy pet owner plan daily care tasks across multiple pets. You tell it how much time you have, add your pets and their tasks, and it builds a schedule that fits — sorted by priority, with real start times and conflict warnings.

---

## Features

**Multiple pets, one schedule**
Add as many pets as you want. Each pet has its own task list. The scheduler pulls everything together into one daily plan.

**Priority-based scheduling**
Tasks are sorted high → medium → low before fitting them into your time budget. Within the same priority, shorter tasks go first to squeeze in as much as possible.

**Real start times**
Every scheduled task gets an actual `HH:MM` start time, beginning at 08:00 and running forward. You see a real timeline, not just a list.

**Recurring tasks**
Set a task to `daily`, `weekly`, or `as-needed`. When you mark it done, the next occurrence is created automatically — tomorrow for daily, 7 days out for weekly. As-needed tasks don't auto-repeat.

**Conflict detection**
If two tasks overlap in time, the app shows a warning banner before the schedule so you can fix it. It uses interval math (`a_start < b_end and b_start < a_end`) and never crashes — just warns.

**Filter the schedule**
Mid-day you can filter the schedule by pet name or by done/pending status to focus on what's left.

**Plan explanation**
After generating a plan, you can see a plain-English breakdown of why each task was scheduled or skipped.

---

## Running the app

```bash
py -m streamlit run app.py
```

Opens at `http://localhost:8501`.

---

## Testing PawPal+

```bash
py -m pytest tests/test_pawpal.py -v
```

37 tests covering:
- tasks fitting (or not) into the time budget
- priority sort order regardless of input order
- recurring task auto-creation (daily, weekly, as-needed)
- conflict detection — overlaps flagged, back-to-back ok
- filtering by pet and status
- edge cases: no pets, no tasks, zero minutes, completing a task twice

**Confidence: 4/5** — core logic is solid; conflict checker is O(n²) which is fine at daily pet-care scale.

---

## System Design

The app is built on four classes in `pawpal_system.py`:

| Class | Responsibility |
|---|---|
| `CareTask` | One activity — name, duration, priority, frequency, due date |
| `Pet` | Owns a list of tasks, handles completion and recurrence |
| `Owner` | Holds multiple pets, aggregates tasks for the scheduler |
| `Scheduler` | Builds the plan, assigns times, detects conflicts, filters |

UML diagram: [`design/class_diagram.mmd`](design/class_diagram.mmd)

---

## 📸 Demo

![PawPal App Demo 1](demo1.png)

![PawPal App Demo 2](demo2.png)

---

## Project workflow

1. Read the scenario and identify requirements.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs.
4. Implement scheduling logic in small steps.
5. Add tests to verify key behaviors.
6. Connect logic to the Streamlit UI in `app.py`.
7. Refine UML to match what was actually built.
