"""
Kindred v2.5.2 - Questionnaire Definitions
Validated psychometric items, scenario-based questions, forced trade-offs,
behavioral items, self-disclosure, communication style, financial values,
and dating energy/intent questions for comprehensive compatibility matching.
"""

import math

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

# The original onboarding items remain the stable, hand-written core. The
# larger bank below is generated from reviewed stems and contexts so new
# clients can sample adaptively without shipping a thousand lines of nearly
# identical literals.
BIG_FIVE_CORE_ITEMS = tuple(BIG_FIVE_ITEMS)

_IRT_BANK_SPEC = {
    "openness": {
        "contexts": (
            "travel and culture", "music and art", "food and cooking",
            "science and technology", "history and current events",
            "different ways of living", "creative projects", "new hobbies",
            "unfamiliar viewpoints", "books and stories", "local traditions",
            "language and communication", "design and architecture",
            "nature and the environment", "philosophy and meaning",
            "new work methods", "community ideas", "relationships and identity",
            "questions without clear answers", "unexpected experiences",
        ),
        "stems": (
            ("I enjoy exploring unfamiliar {context}.", False),
            ("I like learning how other people approach {context}.", False),
            ("I seek out conversations about {context}.", False),
            ("I get excited by a new perspective on {context}.", False),
            ("I connect ideas from {context} in unexpected ways.", False),
            ("I prefer familiar opinions about {context}.", True),
            ("I avoid changing my view on {context}.", True),
            ("I rarely wonder why people experience {context} differently.", True),
            ("New approaches to {context} usually feel unnecessary to me.", True),
            ("I would rather repeat a familiar approach to {context} than experiment.", True),
        ),
    },
    "conscientiousness": {
        "contexts": (
            "appointments", "household chores", "work deadlines", "travel plans",
            "monthly finances", "health routines", "shared commitments",
            "long-term projects", "daily errands", "important conversations",
            "digital files", "event planning", "learning goals", "meal planning",
            "follow-up messages", "renewals and paperwork", "personal budgets",
            "morning routines", "group responsibilities", "future plans",
        ),
        "stems": (
            ("I make a plan before handling {context}.", False),
            ("I keep track of details in {context}.", False),
            ("I follow through on {context} even when I am tired.", False),
            ("I set reminders for {context} when they matter.", False),
            ("I usually finish {context} earlier than necessary.", False),
            ("I often leave {context} until the last minute.", True),
            ("I lose track of {context} easily.", True),
            ("I make promises about {context} before checking my schedule.", True),
            ("I put off organizing {context} until it becomes urgent.", True),
            ("I rarely prepare for {context} in advance.", True),
        ),
    },
    "extraversion": {
        "contexts": (
            "neighborhood gatherings", "work events", "group trips", "parties",
            "new classes", "community projects", "team meetings", "busy cafes",
            "family celebrations", "online communities", "concerts", "sports events",
            "shared meals", "volunteer activities", "networking conversations",
            "public celebrations", "weekend plans", "introductions", "group chats",
            "unfamiliar social settings",
        ),
        "stems": (
            ("I feel energized by social {context}.", False),
            ("I am comfortable starting a conversation during {context}.", False),
            ("I look forward to meeting people through {context}.", False),
            ("I tend to make {context} more lively.", False),
            ("I often suggest {context} when making plans.", False),
            ("I prefer to stay on the edge of {context}.", True),
            ("I feel drained after most {context}.", True),
            ("I avoid speaking first during {context}.", True),
            ("I would rather skip {context} than make small talk.", True),
            ("I need a long time alone after {context}.", True),
        ),
    },
    "agreeableness": {
        "contexts": (
            "disagreements", "shared decisions", "busy days", "family tension",
            "friendship changes", "group projects", "different priorities",
            "difficult feedback", "misunderstandings", "plans that change",
            "household negotiations", "competing needs", "honest conversations",
            "supporting a partner", "community disagreements", "apologies",
            "workplace conflict", "boundary discussions", "unexpected requests",
            "repairing trust",
        ),
        "stems": (
            ("I try to understand another person's view during {context}.", False),
            ("I look for a fair solution in {context}.", False),
            ("I notice when someone needs support during {context}.", False),
            ("I can disagree without making {context} personal.", False),
            ("I am willing to compromise during {context}.", False),
            ("I assume people are being difficult during {context}.", True),
            ("I focus on winning rather than understanding in {context}.", True),
            ("I find it hard to forgive after {context}.", True),
            ("I dismiss other people's concerns during {context}.", True),
            ("I would rather withdraw than cooperate during {context}.", True),
        ),
    },
    "stability": {
        "contexts": (
            "uncertain plans", "unexpected news", "busy weeks", "relationship change",
            "financial pressure", "health concerns", "public mistakes", "long waits",
            "conflicting messages", "new responsibilities", "last-minute changes",
            "difficult decisions", "work pressure", "unfamiliar places", "bad weather",
            "social tension", "unresolved questions", "major transitions",
            "disappointing results", "quiet evenings",
        ),
        "stems": (
            ("I can stay calm when {context} becomes uncertain.", False),
            ("I recover quickly after {context}.", False),
            ("I can think clearly during {context}.", False),
            ("I keep small setbacks in perspective during {context}.", False),
            ("I trust myself to handle {context}.", False),
            ("I worry about everything that could go wrong with {context}.", True),
            ("I replay {context} in my head for a long time.", True),
            ("I feel overwhelmed quickly by {context}.", True),
            ("I expect {context} to turn out badly.", True),
            ("I have trouble relaxing after {context}.", True),
        ),
    },
}

IRT_ITEM_PARAMS = {
    item[0]: {
        "trait": item[2],
        "discrimination": 1.15,
        "difficulty": 0.0,
    }
    for item in BIG_FIVE_CORE_ITEMS
}


def _build_irt_item_bank() -> list[tuple[str, str, str, bool]]:
    items = []
    for trait, spec in _IRT_BANK_SPEC.items():
        trait_code = trait[:3]
        for stem_index, (stem, reverse) in enumerate(spec["stems"]):
            for context_index, context in enumerate(spec["contexts"]):
                item_id = f"irt_{trait_code}_{stem_index + 1:02d}_{context_index + 1:02d}"
                discrimination = 0.8 + ((stem_index * 11 + context_index * 7) % 15) / 10
                difficulty = ((context_index % 10) - 4.5) / 2
                difficulty += ((stem_index % 4) - 1.5) * 0.25
                IRT_ITEM_PARAMS[item_id] = {
                    "trait": trait,
                    "discrimination": round(discrimination, 2),
                    "difficulty": round(difficulty, 2),
                }
                items.append((item_id, stem.format(context=context), trait, reverse))
    return items


BIG_FIVE_ITEMS = list(BIG_FIVE_CORE_ITEMS) + _build_irt_item_bank()
_BIG_FIVE_BY_ID = {item[0]: item for item in BIG_FIVE_ITEMS}


def _logistic(value: float) -> float:
    value = max(-60.0, min(60.0, value))
    return 1.0 / (1.0 + math.exp(-value))


def irt_item_information(item_id: str, ability: float = 0.0) -> float:
    """Return Fisher information for a 2PL item at a trait ability estimate."""
    params = IRT_ITEM_PARAMS.get(item_id)
    if not params:
        return 0.0
    discrimination = params["discrimination"]
    probability = _logistic(discrimination * (ability - params["difficulty"]))
    return discrimination ** 2 * probability * (1.0 - probability)


def estimate_trait_abilities(answers: dict[str, int] | None = None) -> dict[str, float]:
    """Estimate each Big Five ability on the IRT theta scale from answers."""
    trait_values: dict[str, list[float]] = {}
    for item_id, answer in (answers or {}).items():
        item = _BIG_FIVE_BY_ID.get(str(item_id))
        if not item:
            continue
        try:
            value = float(answer)
        except (TypeError, ValueError):
            continue
        if not 1.0 <= value <= 5.0:
            continue
        normalized = (value - 3.0) / 2.0
        if item[3]:
            normalized *= -1.0
        trait_values.setdefault(item[2], []).append(normalized * 3.0)
    return {
        trait: round(max(-3.0, min(3.0, sum(values) / len(values))), 4)
        for trait, values in trait_values.items()
        if values
    }


def select_adaptive_big_five_items(
    excluded_ids: set[str] | None = None,
    answers: dict[str, int] | None = None,
    limit: int = 24,
) -> list[tuple[str, str, str, bool]]:
    """Select unanswered items with the highest expected information."""
    excluded = {str(item_id) for item_id in (excluded_ids or set())}
    abilities = estimate_trait_abilities(answers)
    ranked = []
    for item in BIG_FIVE_ITEMS:
        if item[0] in excluded:
            continue
        theta = abilities.get(item[2], 0.0)
        ranked.append((irt_item_information(item[0], theta), item))
    ranked.sort(key=lambda entry: (-entry[0], entry[1][0]))
    return [item for _, item in ranked[:max(0, int(limit))]]

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
# Active-learning question selection
# ---------------------------------------------------------------------------

_ADAPTIVE_SPECS = None


def _adaptive_question_specs() -> list[dict]:
    """Build the normalized question view used by adaptive clients."""
    global _ADAPTIVE_SPECS
    if _ADAPTIVE_SPECS is not None:
        return _ADAPTIVE_SPECS

    specs = []

    def add(question: dict, dimension: str, field: str, key=None, kind="choice", trait=None):
        specs.append({
            "id": question["id"],
            "dimension": dimension,
            "field": field,
            "key": key,
            "kind": kind,
            "trait": trait,
            "question": question,
        })

    for item_id, text, trait, _reverse in BIG_FIVE_ITEMS:
        add(
            {"id": item_id, "text": text, "type": "likert", "trait": trait},
            "personality", "big_five_answers", item_id, "irt", trait,
        )

    for scenario in SCENARIO_QUESTIONS:
        add(
            {
                "id": scenario["id"],
                "text": scenario["text"],
                "type": "scenario",
                "options": [option["label"] for option in scenario["options"]],
            },
            "personality", "scenario_answers", scenario["id"],
        )

    for behavioral in BEHAVIORAL_QUESTIONS:
        add(
            {key: value for key, value in behavioral.items() if key != "trait_map"},
            "personality", "behavioral_answers", behavioral["id"],
        )

    for value_question in VALUES_QUESTIONS:
        add(
            dict(value_question), "values", "values", value_question["id"],
        )

    for tradeoff in TRADEOFF_QUESTIONS:
        add(dict(tradeoff), "tradeoffs", "tradeoffs", tradeoff["id"])

    for disclosure in SELF_DISCLOSURE:
        add(dict(disclosure), "dealbreaker", "self_disclosure", disclosure["id"])

    for attachment_id, text, style, _reverse in ATTACHMENT_ITEMS:
        add(
            {"id": attachment_id, "text": text, "type": "likert", "trait": style},
            "attachment", "attachment_answers", attachment_id,
        )

    for communication in COMMUNICATION_QUESTIONS:
        add(dict(communication), "communication", "communication_style", communication["id"])

    for financial in FINANCIAL_QUESTIONS:
        add(dict(financial), "financial", "financial_values", financial["id"])

    energy_fields = {
        "dating_energy": "dating_energy",
        "dating_pace": "dating_pace",
        "relationship_intent": "relationship_intent",
    }
    for energy in ENERGY_QUESTIONS:
        add(
            dict(energy), "values", energy_fields[energy["id"]],
            kind="choice",
        )

    for prompt in OPEN_ENDED_PROMPTS:
        add(
            {**prompt, "type": "textarea"}, "semantic", "open_ended", prompt["id"],
        )

    _ADAPTIVE_SPECS = specs
    return specs


def _adaptive_answer(spec: dict, answers: dict) -> object:
    field = spec["field"]
    if spec["key"] is None:
        return answers.get(field)
    values = answers.get(field, {})
    if not isinstance(values, dict):
        return None
    return values.get(spec["key"])


def _adaptive_base_information(spec: dict, abilities: dict[str, float]) -> float:
    if spec["kind"] == "irt":
        return irt_item_information(spec["id"], abilities.get(spec["trait"], 0.0))

    question = spec["question"]
    options = question.get("options") or question.get("labels") or []
    if len(options) >= 2:
        return 1.0 + math.log2(len(options))
    return 0.75


def select_next_adaptive_question(
    answers: dict | None = None,
    asked_ids: set[str] | None = None,
) -> dict | None:
    """Return the unanswered prompt with the highest expected information gain."""
    answers = answers if isinstance(answers, dict) else {}
    asked = {str(item_id) for item_id in (asked_ids or set())}
    abilities = estimate_trait_abilities(answers.get("big_five_answers", {}))
    specs = _adaptive_question_specs()
    dimension_totals: dict[str, int] = {}
    dimension_answered: dict[str, int] = {}

    for spec in specs:
        dimension = spec["dimension"]
        dimension_totals[dimension] = dimension_totals.get(dimension, 0) + 1
        if _adaptive_answer(spec, answers) not in (None, "", []):
            dimension_answered[dimension] = dimension_answered.get(dimension, 0) + 1

    # A small target per dimension prevents the 1,000-item personality bank
    # from crowding out lower-volume dimensions during the early interview.
    targets = {
        "personality": 8,
        "values": 5,
        "communication": 3,
        "financial": 3,
        "attachment": 3,
        "tradeoffs": 3,
        "dealbreaker": 4,
        "semantic": 2,
    }
    ranked = []
    for spec in specs:
        if spec["id"] in asked or _adaptive_answer(spec, answers) not in (None, "", []):
            continue
        dimension = spec["dimension"]
        base_information = _adaptive_base_information(spec, abilities)
        target = targets.get(dimension, min(dimension_totals[dimension], 4))
        coverage = min(1.0, dimension_answered.get(dimension, 0) / target)
        coverage_factor = max(0.15, 1.0 - coverage)
        gain = base_information * coverage_factor
        ranked.append((gain, base_information, spec))

    if not ranked:
        return None
    ranked.sort(key=lambda item: (-item[0], -item[1], item[2]["id"]))
    gain, base_information, selected = ranked[0]
    question = dict(selected["question"])
    question.update({
        "dimension": selected["dimension"],
        "expected_information_gain": round(gain, 4),
        "item_information": round(base_information, 4),
        "field": selected["field"],
        "key": selected["key"],
    })
    return question

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


REGIONAL_NORM_VERSION = 1
REGIONAL_NORM_MIN_SAMPLE = 20
_GLOBAL_TRAIT_MEAN = 0.5
_GLOBAL_TRAIT_STD = 0.2
_COUNTRY_ALIASES = {
    "UNITED STATES": "US",
    "USA": "US",
    "UNITED KINGDOM": "GB",
    "UK": "GB",
    "GREAT BRITAIN": "GB",
    "CANADA": "CA",
    "AUSTRALIA": "AU",
}


def normalize_country_code(country: str | None) -> str:
    """Normalize a user-supplied country label for cohort grouping."""
    if not isinstance(country, str):
        return ""
    normalized = " ".join(country.strip().upper().split())
    return _COUNTRY_ALIASES.get(normalized, normalized)


def build_regional_norm_table(
    profiles: list[dict] | None = None,
    min_sample: int = REGIONAL_NORM_MIN_SAMPLE,
) -> dict[str, dict]:
    """Build versioned, local-cohort Big Five norms from retained raw scores."""
    cohorts: dict[str, dict[str, list[float]]] = {}
    for profile in profiles or []:
        if not isinstance(profile, dict):
            continue
        country = normalize_country_code(profile.get("country"))
        raw_scores = profile.get("big_five_raw") or profile.get("big_five") or {}
        if not country or not isinstance(raw_scores, dict):
            continue
        country_scores = cohorts.setdefault(country, {})
        for trait, value in raw_scores.items():
            try:
                score = float(value)
            except (TypeError, ValueError):
                continue
            if 0.0 <= score <= 1.0:
                country_scores.setdefault(trait, []).append(score)

    table = {}
    for country, trait_scores in cohorts.items():
        means = {}
        stds = {}
        sample_sizes = {}
        for trait, scores in trait_scores.items():
            if not scores:
                continue
            mean = sum(scores) / len(scores)
            variance = sum((score - mean) ** 2 for score in scores) / len(scores)
            means[trait] = round(mean, 4)
            # A floor prevents a tiny local spread from producing extreme z-scores.
            stds[trait] = round(max(math.sqrt(variance), 0.15), 4)
            sample_sizes[trait] = len(scores)
        table[country] = {
            "version": REGIONAL_NORM_VERSION,
            "source": "local-cohort",
            "sample_size": max(sample_sizes.values(), default=0),
            "min_sample": min_sample,
            "means": means,
            "stds": stds,
            "sample_sizes": sample_sizes,
        }
    return table


def calibrate_big_five(
    raw_scores: dict[str, float],
    country: str | None = None,
    regional_norms: dict[str, dict] | None = None,
    min_sample: int = REGIONAL_NORM_MIN_SAMPLE,
) -> dict[str, float]:
    """Center a score against a sufficiently large country cohort.

    Scores remain unchanged when country data is missing or under-sampled.
    """
    if not isinstance(raw_scores, dict):
        return {}
    country_code = normalize_country_code(country)
    entry = (regional_norms or {}).get(country_code)
    calibrated = {}
    for trait, value in raw_scores.items():
        try:
            score = float(value)
        except (TypeError, ValueError):
            continue
        if not entry or entry.get("sample_sizes", {}).get(trait, 0) < min_sample:
            calibrated[trait] = round(score, 4)
            continue
        mean = float(entry.get("means", {}).get(trait, _GLOBAL_TRAIT_MEAN))
        std = max(float(entry.get("stds", {}).get(trait, _GLOBAL_TRAIT_STD)), 0.15)
        centered = _GLOBAL_TRAIT_MEAN + ((score - mean) / std) * _GLOBAL_TRAIT_STD
        calibrated[trait] = round(max(0.01, min(0.99, centered)), 4)
    return calibrated


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
