"""
Kindred v2.1.0 - Questionnaire Definitions
Validated psychometric items, scenario-based questions, forced trade-offs,
behavioral items, self-disclosure, communication style, financial values,
and dating energy/intent questions for comprehensive compatibility matching.
"""

# ---------------------------------------------------------------------------
# Big Five (BFI-2-XS inspired, 15 items, 3 per trait)
# Each item: (id, text, trait, reverse_scored)
# Scale: 1 = Strongly Disagree ... 5 = Strongly Agree
# ---------------------------------------------------------------------------
BIG_FIVE_ITEMS = [
    # Openness
    ("o1", "I enjoy exploring new ideas and perspectives.", "openness", False),
    ("o2", "I have a vivid imagination.", "openness", False),
    ("o3", "I prefer sticking to what I know over trying new things.", "openness", True),
    # Conscientiousness
    ("c1", "I keep my commitments and follow through on plans.", "conscientiousness", False),
    ("c2", "I keep my living and work spaces organized.", "conscientiousness", False),
    ("c3", "I tend to put off important tasks.", "conscientiousness", True),
    # Extraversion
    ("e1", "I feel energized after spending time with groups of people.", "extraversion", False),
    ("e2", "I'm usually the one to start conversations with strangers.", "extraversion", False),
    ("e3", "I prefer quiet nights in over going out.", "extraversion", True),
    # Agreeableness
    ("a1", "I go out of my way to help others, even when it's inconvenient.", "agreeableness", False),
    ("a2", "I try to see things from other people's point of view.", "agreeableness", False),
    ("a3", "I find it hard to compromise in disagreements.", "agreeableness", True),
    # Emotional Stability (reverse of Neuroticism)
    ("n1", "I stay calm and collected under pressure.", "stability", False),
    ("n2", "I worry a lot about things that might go wrong.", "stability", True),
    ("n3", "My mood shifts frequently throughout the day.", "stability", True),
]

# ---------------------------------------------------------------------------
# Scenario-Based Questions (reveal behavior, not self-perception)
# Each option maps to trait scores: {trait: delta}
# ---------------------------------------------------------------------------
SCENARIO_QUESTIONS = [
    {
        "id": "sc1",
        "text": "Your partner cancels plans last minute because something came up at work. You:",
        "options": [
            {"label": "Feel hurt but don't mention it", "traits": {"agreeableness": 0.3, "stability": -0.2, "at_anxious": 0.3}},
            {"label": "Tell them directly how it makes you feel", "traits": {"stability": 0.3, "agreeableness": 0.1, "at_secure": 0.3}},
            {"label": "Shrug it off and make other plans", "traits": {"stability": 0.4, "extraversion": 0.2, "at_avoidant": 0.2}},
            {"label": "Need some time alone to process before responding", "traits": {"stability": 0.1, "extraversion": -0.2, "at_avoidant": 0.2}},
        ],
    },
    {
        "id": "sc2",
        "text": "You and your partner disagree on a major financial decision. You:",
        "options": [
            {"label": "Compromise quickly to avoid conflict", "traits": {"agreeableness": 0.4, "conscientiousness": -0.1}},
            {"label": "Research both options and present the facts", "traits": {"conscientiousness": 0.4, "openness": 0.2}},
            {"label": "Stand firm on your position", "traits": {"agreeableness": -0.3, "stability": 0.2}},
            {"label": "Table it and revisit when emotions have cooled", "traits": {"stability": 0.4, "agreeableness": 0.2}},
        ],
    },
    {
        "id": "sc3",
        "text": "A friend invites you to a party where you won't know anyone else. You:",
        "options": [
            {"label": "Excited! Love meeting new people", "traits": {"extraversion": 0.5, "openness": 0.3}},
            {"label": "Go, but stay close to your friend", "traits": {"extraversion": 0.1, "agreeableness": 0.2}},
            {"label": "Suggest a smaller gathering instead", "traits": {"extraversion": -0.2, "agreeableness": 0.1}},
            {"label": "Politely decline \u2014 not your scene", "traits": {"extraversion": -0.4}},
        ],
    },
    {
        "id": "sc4",
        "text": "You receive unexpected harsh criticism at work. Your first reaction:",
        "options": [
            {"label": "Replay it in your head for days", "traits": {"stability": -0.4, "at_anxious": 0.2}},
            {"label": "Consider if there's truth to it and adjust", "traits": {"stability": 0.3, "openness": 0.3}},
            {"label": "Brush it off \u2014 doesn't define you", "traits": {"stability": 0.4}},
            {"label": "Vent to someone you trust to feel better", "traits": {"extraversion": 0.2, "at_anxious": 0.1}},
        ],
    },
    {
        "id": "sc5",
        "text": "Your ideal Saturday morning:",
        "options": [
            {"label": "Sleep in, then coffee and a book or show", "traits": {"extraversion": -0.3, "openness": 0.1}},
            {"label": "Hit the gym, then brunch with friends", "traits": {"extraversion": 0.3, "conscientiousness": 0.2}},
            {"label": "Tackle your to-do list and errands", "traits": {"conscientiousness": 0.4, "extraversion": -0.1}},
            {"label": "Explore a new trail, cafe, or neighborhood", "traits": {"openness": 0.4, "extraversion": 0.1}},
        ],
    },
]

# ---------------------------------------------------------------------------
# Forced Trade-Offs (reveal real priorities when both are desirable)
# Each pair: user picks A or B. Stored as the chosen label.
# ---------------------------------------------------------------------------
TRADEOFF_QUESTIONS = [
    {
        "id": "to1",
        "text": "Would you rather have a partner who is...",
        "option_a": "Ambitious and driven, but often busy",
        "option_b": "Always available and present, but less career-focused",
    },
    {
        "id": "to2",
        "text": "Would you rather have a partner who...",
        "option_a": "Shares all your interests and hobbies",
        "option_b": "Challenges you to try new things you'd never pick yourself",
    },
    {
        "id": "to3",
        "text": "What matters more to you in a relationship?",
        "option_a": "Deep emotional intimacy, even if it means occasional conflict",
        "option_b": "Peaceful harmony, even if it means less emotional depth",
    },
    {
        "id": "to4",
        "text": "Would you rather have a partner who is...",
        "option_a": "Spontaneous and exciting, but unpredictable",
        "option_b": "Reliable and steady, but sometimes predictable",
    },
    {
        "id": "to5",
        "text": "Which would be harder to deal with?",
        "option_a": "A partner your family doesn't connect with, but who shares your values",
        "option_b": "A partner your family loves, but who has different core values",
    },
]

# ---------------------------------------------------------------------------
# Behavioral Questions (observable actions, not self-assessment)
# ---------------------------------------------------------------------------
BEHAVIORAL_QUESTIONS = [
    {
        "id": "bh1",
        "text": "How many close friends do you actively keep in touch with?",
        "type": "choice",
        "options": ["0-1", "2-3", "4-6", "7+"],
        "trait_map": {"extraversion": [0.1, 0.35, 0.65, 0.9]},
    },
    {
        "id": "bh2",
        "text": "When did you last try something completely new?",
        "type": "choice",
        "options": ["This week", "This month", "A few months ago", "Can't remember"],
        "trait_map": {"openness": [0.9, 0.7, 0.4, 0.15]},
    },
    {
        "id": "bh3",
        "text": "How do you typically spend the first hour after waking up?",
        "type": "choice",
        "options": ["Phone / social media", "Exercise or movement", "Slow morning routine", "Jump straight into tasks"],
        "trait_map": {"conscientiousness": [0.2, 0.8, 0.5, 0.7]},
    },
    {
        "id": "bh4",
        "text": "When you're stressed, you tend to:",
        "type": "choice",
        "options": ["Talk to someone about it", "Exercise or do something physical", "Withdraw and recharge alone", "Distract yourself with something fun"],
        "trait_map": {"extraversion": [0.8, 0.5, 0.15, 0.4], "stability": [0.6, 0.7, 0.4, 0.3]},
    },
]

# ---------------------------------------------------------------------------
# Self-Disclosure (maps to dealbreaker matching)
# These are facts about the user that can trigger another user's dealbreakers.
# ---------------------------------------------------------------------------
SELF_DISCLOSURE = [
    {
        "id": "sd_smoking",
        "text": "Do you smoke?",
        "options": ["Never", "Socially / rarely", "Regularly"],
        "maps_to_dealbreaker": "Smoking",
        "trigger_values": ["Socially / rarely", "Regularly"],
    },
    {
        "id": "sd_drinking",
        "text": "How often do you drink alcohol?",
        "options": ["Never", "Socially / occasionally", "Weekly", "Daily"],
        "maps_to_dealbreaker": "Heavy drinking",
        "trigger_values": ["Daily"],
    },
    {
        "id": "sd_drugs",
        "text": "Do you use recreational drugs?",
        "options": ["Never", "Rarely / socially", "Regularly"],
        "maps_to_dealbreaker": "Recreational drug use",
        "trigger_values": ["Rarely / socially", "Regularly"],
    },
    {
        "id": "sd_has_kids",
        "text": "Do you currently have children?",
        "options": ["No", "Yes"],
        "maps_to_dealbreaker": "Already has kids",
        "trigger_values": ["Yes"],
    },
    {
        "id": "sd_ambition",
        "text": "How would you describe your career drive?",
        "options": ["Highly ambitious", "Motivated but balanced", "Work to live", "Currently figuring it out"],
        "maps_to_dealbreaker": "No career ambition",
        "trigger_values": ["Currently figuring it out"],
    },
    {
        "id": "sd_commitment",
        "text": "Are you ready for a serious, committed relationship?",
        "options": ["Absolutely, that's why I'm here", "I think so", "Still figuring that out"],
        "maps_to_dealbreaker": "Not ready to commit",
        "trigger_values": ["Still figuring that out"],
    },
]

# ---------------------------------------------------------------------------
# Communication Style (4 items)
# Used for communication compatibility scoring
# ---------------------------------------------------------------------------
COMMUNICATION_QUESTIONS = [
    {
        "id": "comm_response",
        "text": "How quickly do you typically respond to messages?",
        "options": ["Within minutes", "Within a few hours", "Same day", "When I have something meaningful to say"],
    },
    {
        "id": "comm_conflict",
        "text": "During a disagreement, what's your instinct?",
        "options": ["Talk it out immediately", "Take space to process, then discuss", "Write out my thoughts first", "Avoid conflict when possible"],
    },
    {
        "id": "comm_frequency",
        "text": "How often do you like to text a partner?",
        "options": ["Throughout the day", "A few times a day", "Once or twice a day", "When there's something to share"],
    },
    {
        "id": "comm_serious",
        "text": "How do you prefer to have serious conversations?",
        "options": ["Face to face", "Phone/video call", "Through text/writing", "While doing an activity together"],
    },
]

# ---------------------------------------------------------------------------
# Financial Compatibility (3 items)
# Financial conflict is the #1 predictor of divorce
# ---------------------------------------------------------------------------
FINANCIAL_QUESTIONS = [
    {
        "id": "fin_spending",
        "text": "Your approach to money:",
        "options": ["Save first, spend what's left", "Enjoy today, plan for tomorrow", "Strict budget for everything", "Flexible \u2014 depends on the situation"],
    },
    {
        "id": "fin_debt",
        "text": "How do you feel about debt?",
        "options": ["Avoid it completely", "Only for major investments", "A normal part of life", "Haven't thought much about it"],
    },
    {
        "id": "fin_shared",
        "text": "In a relationship, finances should be:",
        "options": ["Completely shared", "Shared for household, personal accounts too", "Mostly separate with shared expenses", "Completely separate"],
    },
]

# ---------------------------------------------------------------------------
# Dating Energy & Intent (3 items)
# Match users at similar energy levels and relationship intent
# ---------------------------------------------------------------------------
ENERGY_QUESTIONS = [
    {
        "id": "dating_energy",
        "text": "Your current dating energy:",
        "options": ["Actively looking \u2014 ready to meet", "Open but relaxed \u2014 no rush", "Taking it slow \u2014 getting to know people", "Just exploring for now"],
    },
    {
        "id": "dating_pace",
        "text": "How soon do you like to meet in person?",
        "options": ["Within a few days", "Within a week", "After a couple weeks of chatting", "When it feels right, no timeline"],
    },
    {
        "id": "relationship_intent",
        "text": "What are you looking for?",
        "options": ["Marriage / life partner", "Serious committed relationship", "Open to serious if the right person", "Still figuring it out"],
    },
]

# ---------------------------------------------------------------------------
# Values & Lifestyle (structured choices)
# ---------------------------------------------------------------------------
VALUES_QUESTIONS = [
    {
        "id": "v_faith",
        "text": "How important is faith or spirituality in your life?",
        "type": "scale",
        "labels": ["Not at all", "Slightly", "Moderately", "Very", "Extremely"],
    },
    {
        "id": "v_children",
        "text": "Do you want children?",
        "type": "choice",
        "options": ["Definitely not", "Probably not", "Open to it", "Yes, someday", "Yes, definitely", "Already have kids"],
    },
    {
        "id": "v_career_family",
        "text": "How do you balance career ambition and family life?",
        "type": "scale",
        "labels": ["Family first", "Lean family", "Equal balance", "Lean career", "Career first"],
    },
    {
        "id": "v_politics",
        "text": "Where do you fall on the political spectrum?",
        "type": "choice",
        "options": ["Very liberal", "Lean liberal", "Moderate / independent", "Lean conservative", "Very conservative", "Non-political"],
    },
    {
        "id": "v_fitness",
        "text": "How important is physical fitness and health to you?",
        "type": "scale",
        "labels": ["Not important", "Slightly", "Moderately", "Very", "Essential"],
    },
    {
        "id": "v_lifestyle",
        "text": "What best describes your ideal weekend?",
        "type": "choice",
        "options": ["Cozy day at home", "Coffee shop and a book", "Outdoor adventure", "Social gathering with friends", "Exploring somewhere new", "Mix of everything"],
    },
    {
        "id": "v_finances",
        "text": "How would you describe your approach to money?",
        "type": "choice",
        "options": ["Strict saver", "Mostly save, occasional treats", "Balanced", "Enjoy spending, but responsible", "Live in the moment"],
    },
    {
        "id": "v_living",
        "text": "Where do you prefer to live?",
        "type": "choice",
        "options": ["Big city", "Suburbs", "Small town", "Rural / countryside", "Flexible / no preference"],
    },
]

# ---------------------------------------------------------------------------
# Attachment Style (4 items scored to classify)
# ---------------------------------------------------------------------------
ATTACHMENT_ITEMS = [
    ("at1", "I find it easy to get emotionally close to others.", "secure", False),
    ("at2", "I worry that my partner will lose interest in me.", "anxious", False),
    ("at3", "I prefer not to depend on my partner too much.", "avoidant", False),
    ("at4", "I feel comfortable when my partner needs their own space.", "secure", False),
]

# ---------------------------------------------------------------------------
# Love Languages
# ---------------------------------------------------------------------------
LOVE_LANGUAGES = [
    "Words of Affirmation",
    "Quality Time",
    "Physical Touch",
    "Acts of Service",
    "Receiving Gifts",
]

# ---------------------------------------------------------------------------
# Deal-Breakers (multi-select)
# ---------------------------------------------------------------------------
DEALBREAKERS = [
    "Smoking",
    "Heavy drinking",
    "Recreational drug use",
    "Doesn't want kids",
    "Already has kids",
    "Different faith / values",
    "No career ambition",
    "Long-distance only",
    "Not ready to commit",
    "Poor hygiene",
    "Dishonesty",
    "Controlling behavior",
]

# Children-related dealbreaker cross-reference
CHILDREN_DEALBREAKER_MAP = {
    "Definitely not": "Doesn't want kids",
    "Probably not": None,
    "Open to it": None,
    "Yes, someday": None,
    "Yes, definitely": None,
    "Already have kids": "Already has kids",
}

# ---------------------------------------------------------------------------
# Open-Ended Prompts (for semantic embedding)
# ---------------------------------------------------------------------------
OPEN_ENDED_PROMPTS = [
    {
        "id": "oe1",
        "text": "What does your ideal relationship look like? Describe your vision of a great partnership.",
    },
    {
        "id": "oe2",
        "text": "What are you most passionate about in life? What drives you?",
    },
    {
        "id": "oe3",
        "text": "What's the most important lesson you've learned about love or relationships?",
    },
]

# ---------------------------------------------------------------------------
# Scoring Functions
# ---------------------------------------------------------------------------

def score_big_five(answers: dict[str, int], scenario_answers: dict[str, int] | None = None,
                   behavioral_answers: dict[str, str] | None = None) -> dict[str, float]:
    """Score Big Five traits from all question types."""
    trait_points: dict[str, list[float]] = {}

    for item_id, text, trait, reverse in BIG_FIVE_ITEMS:
        if item_id not in answers:
            continue
        val = answers[item_id]
        if reverse:
            val = 6 - val
        normalized = (val - 1) / 4
        trait_points.setdefault(trait, []).append(normalized)

    if scenario_answers:
        for sq in SCENARIO_QUESTIONS:
            chosen_idx = scenario_answers.get(sq["id"])
            if chosen_idx is None:
                continue
            if 0 <= chosen_idx < len(sq["options"]):
                chosen = sq["options"][chosen_idx]
                for trait, delta in chosen["traits"].items():
                    if trait.startswith("at_"):
                        continue
                    score = 0.5 + delta
                    trait_points.setdefault(trait, []).append(score)

    if behavioral_answers:
        for bq in BEHAVIORAL_QUESTIONS:
            answer = behavioral_answers.get(bq["id"])
            if answer is None:
                continue
            try:
                idx = bq["options"].index(answer)
            except ValueError:
                continue
            for trait, scores in bq["trait_map"].items():
                if idx < len(scores):
                    trait_points.setdefault(trait, []).append(scores[idx])

    return {
        trait: round(sum(scores) / len(scores), 4)
        for trait, scores in trait_points.items()
        if scores
    }


def classify_attachment(answers: dict[str, int],
                        scenario_answers: dict[str, int] | None = None) -> dict[str, float]:
    """Classify attachment style from Likert items + scenario signals."""
    style_scores: dict[str, list[float]] = {}

    for item_id, text, style, reverse in ATTACHMENT_ITEMS:
        if item_id not in answers:
            continue
        val = answers[item_id]
        if reverse:
            val = 6 - val
        style_scores.setdefault(style, []).append((val - 1) / 4)

    if scenario_answers:
        for sq in SCENARIO_QUESTIONS:
            chosen_idx = scenario_answers.get(sq["id"])
            if chosen_idx is None:
                continue
            if 0 <= chosen_idx < len(sq["options"]):
                chosen = sq["options"][chosen_idx]
                for trait, delta in chosen["traits"].items():
                    if trait.startswith("at_"):
                        style = trait[3:]
                        style_scores.setdefault(style, []).append(0.5 + delta)

    return {
        style: round(sum(scores) / len(scores), 4)
        for style, scores in style_scores.items()
        if scores
    }


def check_hard_dealbreakers(profile_a: dict, profile_b: dict) -> list[str]:
    """Check if either person's dealbreakers are triggered by the other's self-disclosure."""
    conflicts = []
    sd_a = profile_a.get("self_disclosure", {})
    sd_b = profile_b.get("self_disclosure", {})
    db_a = set(profile_a.get("dealbreakers", []))
    db_b = set(profile_b.get("dealbreakers", []))

    for sd_item in SELF_DISCLOSURE:
        b_answer = sd_b.get(sd_item["id"])
        if b_answer and b_answer in sd_item["trigger_values"]:
            if sd_item["maps_to_dealbreaker"] in db_a:
                conflicts.append(f"{profile_a.get('name', 'A')}'s dealbreaker: {sd_item['maps_to_dealbreaker']}")

    for sd_item in SELF_DISCLOSURE:
        a_answer = sd_a.get(sd_item["id"])
        if a_answer and a_answer in sd_item["trigger_values"]:
            if sd_item["maps_to_dealbreaker"] in db_b:
                conflicts.append(f"{profile_b.get('name', 'B')}'s dealbreaker: {sd_item['maps_to_dealbreaker']}")

    val_a = profile_a.get("values", {}).get("v_children")
    val_b = profile_b.get("values", {}).get("v_children")
    if val_a:
        mapped = CHILDREN_DEALBREAKER_MAP.get(val_a)
        if mapped and mapped in db_b:
            conflicts.append(f"{profile_b.get('name', 'B')}'s dealbreaker: {mapped}")
    if val_b:
        mapped = CHILDREN_DEALBREAKER_MAP.get(val_b)
        if mapped and mapped in db_a:
            conflicts.append(f"{profile_a.get('name', 'A')}'s dealbreaker: {mapped}")

    return conflicts


def build_profile_text(data: dict) -> str:
    """Combine all profile data into a single text for embedding."""
    parts = []

    if "big_five" in data:
        bf = data["big_five"]
        parts.append(
            f"Personality: openness={bf.get('openness', 0):.0%}, "
            f"conscientiousness={bf.get('conscientiousness', 0):.0%}, "
            f"extraversion={bf.get('extraversion', 0):.0%}, "
            f"agreeableness={bf.get('agreeableness', 0):.0%}, "
            f"stability={bf.get('stability', 0):.0%}"
        )

    if "values" in data:
        vals = data["values"]
        for q in VALUES_QUESTIONS:
            qid = q["id"]
            if qid in vals:
                answer = vals[qid]
                if q["type"] == "choice":
                    parts.append(f"{q['text']} {answer}")
                elif q["type"] == "scale":
                    label = q["labels"][int(answer) - 1] if 1 <= int(answer) <= len(q["labels"]) else str(answer)
                    parts.append(f"{q['text']} {label}")

    if "tradeoffs" in data:
        for to in TRADEOFF_QUESTIONS:
            answer = data["tradeoffs"].get(to["id"])
            if answer:
                parts.append(f"{to['text']} {answer}")

    if "communication_style" in data:
        cs = data["communication_style"]
        for q in COMMUNICATION_QUESTIONS:
            answer = cs.get(q["id"])
            if answer:
                parts.append(f"{q['text']} {answer}")

    if "financial_values" in data:
        fv = data["financial_values"]
        for q in FINANCIAL_QUESTIONS:
            answer = fv.get(q["id"])
            if answer:
                parts.append(f"{q['text']} {answer}")

    if "love_language" in data:
        parts.append(f"Primary love language: {data['love_language']}")

    for prompt in OPEN_ENDED_PROMPTS:
        key = prompt["id"]
        if key in data.get("open_ended", {}):
            text = data["open_ended"][key]
            if text and text.strip():
                parts.append(text.strip())

    return " | ".join(parts)
