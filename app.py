import base64
import streamlit as st
from pawpal_system import CareTask, Pet, Owner, Scheduler
from rag_advisor import suggest_tasks

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

# ---------------------------------------------------------------------------
# Background image
# ---------------------------------------------------------------------------
with open("assets/pets_bg.jpg", "rb") as f:
    bg_data = base64.b64encode(f.read()).decode()

st.markdown(
    f"""
    <style>
    .stApp {{
        background-image: url("data:image/jpg;base64,{bg_data}");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }}
    /* Keep content readable over the image */
    section[data-testid="stSidebar"],
    .block-container {{
        background-color: rgba(255, 255, 255, 0.88);
        border-radius: 12px;
        padding: 2rem;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Session state initialisation
# ---------------------------------------------------------------------------
if "owner" not in st.session_state:
    st.session_state.owner = None
if "scheduler" not in st.session_state:
    st.session_state.scheduler = None
if "suggestions" not in st.session_state:
    st.session_state.suggestions = []
if "suggest_pet_name" not in st.session_state:
    st.session_state.suggest_pet_name = None

# ---------------------------------------------------------------------------
# Title
# ---------------------------------------------------------------------------
st.title("🐾 PawPal+")
st.caption("A daily pet care planner that fits tasks around your schedule.")

st.divider()

# ---------------------------------------------------------------------------
# Section 1: Owner profile
# ---------------------------------------------------------------------------
st.subheader("1. Owner Profile")

with st.form("owner_form"):
    owner_name = st.text_input("Your name", value="Jordan")
    available_minutes = st.number_input(
        "Time available today (minutes)", min_value=5, max_value=480, value=90
    )
    preferences = st.text_input("Preferences (optional)", placeholder="e.g. prefer morning walks")
    submitted = st.form_submit_button("Save profile")

if submitted:
    existing_pets = st.session_state.owner.pets if st.session_state.owner else []
    st.session_state.owner = Owner(
        name=owner_name,
        available_minutes=int(available_minutes),
        preferences=preferences,
    )
    for pet in existing_pets:
        st.session_state.owner.add_pet(pet)
    st.session_state.scheduler = None   # reset plan when profile changes
    st.success(f"Profile saved for {owner_name} ({available_minutes} min available).")

if st.session_state.owner:
    owner = st.session_state.owner
    st.caption(
        f"Current profile: **{owner.name}** — {owner.available_minutes} min/day"
        + (f" | Preferences: {owner.preferences}" if owner.preferences else "")
    )

st.divider()

# ---------------------------------------------------------------------------
# Section 2: Add a pet
# ---------------------------------------------------------------------------
st.subheader("2. Add a Pet")

if not st.session_state.owner:
    st.info("Save your owner profile above before adding pets.")
else:
    with st.form("pet_form"):
        pet_name = st.text_input("Pet name", value="Luna")
        species   = st.selectbox("Species", ["dog", "cat", "rabbit", "bird", "other"])
        age       = st.number_input("Age (years)", min_value=0, max_value=30, value=2)
        notes     = st.text_input("Notes (optional)", placeholder="e.g. has a bad hip")
        add_pet   = st.form_submit_button("Add pet")

    if add_pet:
        owner = st.session_state.owner
        if owner.get_pet(pet_name):
            st.warning(f"{pet_name} is already in your list.")
        else:
            owner.add_pet(Pet(name=pet_name, species=species, age=age, notes=notes))
            st.success(f"Added {pet_name} the {species}!")

    owner = st.session_state.owner
    if owner.pets:
        st.write("**Your pets:**")
        for pet in owner.pets:
            label = f"🐾 {pet.summary()}"
            if pet.notes:
                label += f" — {pet.notes}"
            st.markdown(label)
    else:
        st.info("No pets added yet.")

st.divider()

# ---------------------------------------------------------------------------
# Section 3: Add a care task
# ---------------------------------------------------------------------------
st.subheader("3. Add a Care Task")

owner = st.session_state.owner
if not owner or not owner.pets:
    st.info("Add at least one pet before adding tasks.")
else:
    with st.form("task_form"):
        pet_options  = [p.name for p in owner.pets]
        selected_pet = st.selectbox("Assign to pet", pet_options)

        col1, col2, col3 = st.columns(3)
        with col1:
            task_name = st.text_input("Task name", value="Morning walk")
        with col2:
            duration = st.number_input("Duration (min)", min_value=1, max_value=240, value=20)
        with col3:
            priority = st.selectbox("Priority", ["high", "medium", "low"])

        col4, col5 = st.columns(2)
        with col4:
            category  = st.selectbox("Category", ["walk", "feeding", "meds", "grooming", "enrichment", "other"])
        with col5:
            frequency = st.selectbox("Frequency", ["daily", "weekly", "as-needed"])

        add_task = st.form_submit_button("Add task")

    if add_task:
        pet = owner.get_pet(selected_pet)
        try:
            pet.add_task(CareTask(
                name=task_name,
                duration_minutes=int(duration),
                priority=priority,
                category=category,
                frequency=frequency,
            ))
            st.success(f"Added '{task_name}' to {selected_pet}'s task list.")
            st.session_state.scheduler = None   # stale plan — needs regenerating
        except ValueError as e:
            st.error(str(e))

    # Show all tasks grouped by pet
    all_pairs = owner.get_all_tasks()
    if all_pairs:
        st.write("**All current tasks:**")

        # Group by pet for a cleaner display
        for pet in owner.pets:
            pet_tasks = [(p, t) for p, t in all_pairs if p.name == pet.name]
            if not pet_tasks:
                continue
            st.markdown(f"*{pet.summary()}*")
            rows = [
                {
                    "Task": t.name,
                    "Duration (min)": t.duration_minutes,
                    "Priority": t.priority,
                    "Category": t.category,
                    "Frequency": t.frequency,
                    "Done": "Yes" if t.completed else "No",
                    "Due": t.due_date.isoformat(),
                }
                for _, t in pet_tasks
            ]
            st.table(rows)
    else:
        st.info("No tasks added yet.")

st.divider()

# ---------------------------------------------------------------------------
# Section 4: AI Task Suggestions (RAG)
# ---------------------------------------------------------------------------
st.subheader("4. Get AI Task Suggestions")
st.caption("Let Gemini review your pet's profile and suggest tasks you may have missed.")

owner = st.session_state.owner
if not owner or not owner.pets:
    st.info("Add at least one pet above to get AI-powered task suggestions.")
else:
    pet_names = [p.name for p in owner.pets]
    suggest_pet_name = st.selectbox("Get suggestions for", pet_names, key="suggest_pet")

    if st.button("Ask Gemini for suggestions", type="secondary"):
        pet = owner.get_pet(suggest_pet_name)
        with st.spinner(f"Asking Gemini for {pet.name}..."):
            suggestions = suggest_tasks(pet)
        st.session_state.suggestions = suggestions
        st.session_state.suggest_pet_name = suggest_pet_name

    if st.session_state.suggestions and st.session_state.suggest_pet_name:
        suggestions     = st.session_state.suggestions
        target_pet_name = st.session_state.suggest_pet_name

        avg_conf = sum(s["confidence"] for s in suggestions) / len(suggestions)
        st.success(
            f"{len(suggestions)} suggestions for **{target_pet_name}** "
            f"— avg confidence {avg_conf:.0%}"
        )

        selected = []
        for i, s in enumerate(suggestions):
            conf = s.get("confidence", 0.0)
            if conf >= 0.8:
                badge = ":green[High]"
            elif conf >= 0.5:
                badge = ":orange[Medium]"
            else:
                badge = ":red[Low]"

            col_chk, col_info = st.columns([1, 8])
            with col_chk:
                accept = st.checkbox("", key=f"accept_{i}", value=True)
            with col_info:
                st.markdown(
                    f"**{s['name']}** &nbsp;|&nbsp; {s['duration_minutes']} min "
                    f"&nbsp;|&nbsp; `{s['priority']}` priority "
                    f"&nbsp;|&nbsp; {s['frequency']} "
                    f"&nbsp;|&nbsp; Confidence: {badge} ({conf:.0%})"
                )
            if accept:
                selected.append(s)

        if st.button("Add selected tasks to schedule", type="primary", key="add_ai_tasks"):
            pet   = owner.get_pet(target_pet_name)
            added = 0
            for s in selected:
                try:
                    pet.add_task(CareTask(
                        name=s["name"],
                        duration_minutes=int(s["duration_minutes"]),
                        priority=s["priority"],
                        category=s.get("category", "other"),
                        frequency=s.get("frequency", "daily"),
                    ))
                    added += 1
                except ValueError as e:
                    st.warning(f"Skipped '{s['name']}': {e}")
            st.success(f"Added {added} task(s) to {target_pet_name}.")
            st.session_state.suggestions = []
            st.session_state.suggest_pet_name = None
            st.session_state.scheduler = None

    elif st.session_state.get("suggest_pet_name") and not st.session_state.suggestions:
        st.warning("No suggestions returned. Check your GEMINI_API_KEY or see pawpal_rag.log for details.")

st.divider()

# ---------------------------------------------------------------------------
# Section 5: Generate schedule
# ---------------------------------------------------------------------------
st.subheader("5. Generate Today's Schedule")

PRIORITY_ICON = {"high": "🔴", "medium": "🟡", "low": "🟢"}

owner = st.session_state.owner
if not owner or not owner.get_all_pending_tasks():
    st.info("Add an owner, at least one pet, and at least one task to generate a schedule.")
else:
    col_gen, col_filter = st.columns([2, 1])
    with col_gen:
        if st.button("Generate schedule", type="primary"):
            scheduler = Scheduler(owner)
            scheduler.generate_plan()
            st.session_state.scheduler = scheduler

    if st.session_state.scheduler:
        scheduler  = st.session_state.scheduler
        total_min  = sum(t.duration_minutes for _, t in scheduler.scheduled_tasks)
        time_left  = owner.available_minutes - total_min

        # --- Summary bar ---
        st.success(
            f"Plan ready — **{total_min} min** used out of **{owner.available_minutes} min** "
            f"({time_left} min free)"
        )

        # --- Conflict warnings (shown before the plan so the owner sees them first) ---
        conflicts = scheduler.detect_conflicts()
        if conflicts:
            st.markdown("#### Scheduling Conflicts Detected")
            for conflict in conflicts:
                st.warning(conflict)
            st.caption("These tasks overlap in time. Consider adjusting their start times or durations.")

        # --- Filter controls ---
        with st.expander("Filter the schedule", expanded=False):
            filter_col1, filter_col2 = st.columns(2)
            with filter_col1:
                pet_names   = ["All pets"] + [p.name for p in owner.pets]
                filter_pet  = st.selectbox("Show tasks for", pet_names, key="filter_pet")
            with filter_col2:
                filter_status = st.selectbox("Show status", ["All", "Pending", "Done"], key="filter_status")

        # Apply filters
        display_pairs = scheduler.sort_by_time()   # always show in time order

        if filter_pet != "All pets":
            display_pairs = [(p, t) for p, t in display_pairs if p.name == filter_pet]
        if filter_status == "Pending":
            display_pairs = [(p, t) for p, t in display_pairs if not t.completed]
        elif filter_status == "Done":
            display_pairs = [(p, t) for p, t in display_pairs if t.completed]

        # --- Scheduled task table ---
        if display_pairs:
            st.markdown("#### Scheduled Tasks")
            rows = []
            for pet, task in display_pairs:
                end_min = Scheduler._hhmm_to_minutes(task.start_time) + task.duration_minutes
                end_str = f"{end_min // 60:02d}:{end_min % 60:02d}"
                rows.append({
                    "Time": f"{task.start_time} - {end_str}",
                    "Task": f"{PRIORITY_ICON.get(task.priority, '')} {task.name}",
                    "Pet": pet.name,
                    "Duration": f"{task.duration_minutes} min",
                    "Category": task.category,
                    "Freq": task.frequency,
                    "Done": "Yes" if task.completed else "No",
                })
            st.table(rows)
        else:
            st.info("No tasks match the current filter.")

        # --- Skipped tasks ---
        skipped = scheduler.skipped_tasks
        if skipped:
            with st.expander(f"Skipped tasks ({len(skipped)}) — not enough time", expanded=False):
                for pet, task in skipped:
                    st.markdown(
                        f"- **{task.name}** for {pet.name} "
                        f"| needs {task.duration_minutes} min | priority: `{task.priority}`"
                    )

        # --- Plan explanation ---
        with st.expander("Why this plan?", expanded=False):
            st.text(scheduler.explain_plan())
