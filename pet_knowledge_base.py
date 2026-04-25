"""
Static knowledge base of pet care guidelines, organized by species and age group.
Condition-specific flags are matched against keywords in the pet's notes field.
"""

GUIDELINES: dict[str, dict[str, list[str]]] = {
    "dog": {
        "puppy": [
            "Puppies under 1 year need 3-4 small meals per day.",
            "Puppies need short socialization walks: 5 minutes per month of age, 2-3 times daily.",
            "Puppies need bathroom breaks every 2 hours.",
            "Puppies benefit from 10-15 minute basic obedience training sessions daily.",
            "Vaccination series every 3-4 weeks until 16 weeks old.",
        ],
        "adult": [
            "Adult dogs need 30-60 minutes of exercise daily.",
            "Adult dogs should be fed twice daily (morning and evening).",
            "Monthly flea, tick, and heartworm prevention is recommended.",
            "Daily dental hygiene: tooth brushing or dental chew.",
            "Nail trims every 3-4 weeks.",
            "Annual vet checkup with booster vaccines.",
        ],
        "senior": [
            "Senior dogs (7+ years) need gentler exercise: 20-30 minutes daily.",
            "Senior dogs benefit from low-impact activity and joint supplements.",
            "Bi-annual vet visits recommended for senior dogs.",
            "Monitor weight closely; adjust food portions as metabolism slows.",
            "Daily dental hygiene remains important.",
        ],
    },
    "cat": {
        "kitten": [
            "Kittens need 3-4 small meals per day.",
            "Daily interactive play: 2-3 sessions of 10-15 minutes each.",
            "Litter box should be scooped at least once daily.",
            "Vaccination series needed in early months.",
            "Regular gentle handling to build comfort with humans.",
        ],
        "adult": [
            "Adult cats should be fed twice daily.",
            "Litter box should be scooped daily and fully cleaned weekly.",
            "Daily interactive play: 1-2 sessions of 10-15 minutes.",
            "Annual vet checkup.",
            "Monthly flea prevention for indoor/outdoor cats.",
            "Brush coat weekly (short-haired) or 2-3 times per week (long-haired).",
        ],
        "senior": [
            "Senior cats (11+ years) need consistent twice-daily feeding.",
            "Litter box should be low-sided for easy access.",
            "Annual bloodwork recommended; bi-annual vet visits.",
            "Gentle daily play and enrichment to keep the mind active.",
            "Monitor for changes in thirst, urination, appetite, or weight.",
        ],
    },
    "rabbit": {
        "young": [
            "Young rabbits need unlimited timothy hay as their primary diet.",
            "Introduce leafy greens gradually after 12 weeks.",
            "Litter box should be scooped daily.",
            "At least 2-3 hours of supervised exercise outside the enclosure daily.",
        ],
        "adult": [
            "Rabbits need unlimited timothy hay daily.",
            "Fresh leafy greens daily: about 1 cup per 2 lbs of body weight.",
            "Fresh water must be available at all times.",
            "Litter box scooped daily, fully cleaned weekly.",
            "2+ hours of free-roam exercise daily.",
            "Nail trims every 6-8 weeks.",
            "Annual vet checkup.",
        ],
    },
    "bird": {
        "general": [
            "Fresh food and water daily; remove uneaten fresh food within a few hours.",
            "Cage spot-cleaned daily; deep cleaned weekly.",
            "Out-of-cage social time: 1-2 hours daily.",
            "Rotate enrichment toys weekly.",
            "Annual checkup with an avian vet.",
        ],
    },
    "other": {
        "general": [
            "Provide fresh water daily.",
            "Clean the enclosure regularly according to species needs.",
            "Ensure a species-appropriate diet.",
            "Monitor for signs of illness: lethargy, appetite loss, unusual behavior.",
            "Annual checkup with a vet familiar with your pet's species.",
        ],
    },
}

CONDITION_FLAGS: dict[str, list[str]] = {
    "hip": [
        "Avoid high-impact activity; prefer short, flat walks on soft surfaces.",
        "Consider hydrotherapy or gentle massage for joint pain relief.",
    ],
    "joint": [
        "Low-impact exercise only: short walks, no jumping or stairs.",
        "Joint supplements (glucosamine/chondroitin) may help; consult your vet.",
    ],
    "diabetic": [
        "Diabetic pets require meals and insulin on a strict, consistent schedule.",
        "Monitor for hypoglycemia: weakness, trembling, disorientation.",
        "Keep a daily log of food intake and insulin doses.",
    ],
    "dental": [
        "Daily tooth brushing or dental chew is essential.",
        "Schedule a professional dental cleaning annually.",
    ],
    "overweight": [
        "Measure food portions carefully and limit treats.",
        "Increase low-impact exercise gradually.",
        "Weigh monthly and adjust portions based on progress.",
    ],
    "blind": [
        "Keep furniture arrangement consistent so the pet can navigate by memory.",
        "Use sound or scent cues to guide the pet safely.",
        "Ensure outdoor time is in a secure, fully enclosed area.",
    ],
    "anxious": [
        "Keep daily routines consistent to reduce stress.",
        "Provide a dedicated safe retreat space the pet can always access.",
        "Consult your vet about calming supplements or behavioral therapy.",
    ],
    "indoor": [
        "Indoor pets need enrichment to compensate for limited outdoor stimulation.",
        "Rotate toys and provide window perches or climbing structures.",
    ],
}


def get_age_group(species: str, age: int) -> str:
    """Map a pet's species and age in years to an age-group key in GUIDELINES."""
    if species == "dog":
        if age < 1:
            return "puppy"
        if age < 7:
            return "adult"
        return "senior"
    if species == "cat":
        if age < 1:
            return "kitten"
        if age < 11:
            return "adult"
        return "senior"
    if species == "rabbit":
        return "young" if age < 1 else "adult"
    return "general"


def retrieve(species: str, age: int, notes: str) -> list[str]:
    """
    Return care guidelines relevant to this pet.

    Pulls base guidelines for (species, age_group), then appends any
    condition-flag entries whose keyword appears in the notes string.
    Falls back to "other/general" guidelines for unknown species.
    """
    species_key = species.lower().strip()
    notes_lower = notes.lower()

    age_group = get_age_group(species_key, age)
    species_guides = GUIDELINES.get(species_key, GUIDELINES["other"])
    base = list(species_guides.get(age_group, species_guides.get("general", [])))

    for keyword, extras in CONDITION_FLAGS.items():
        if keyword in notes_lower:
            base.extend(extras)

    return base
