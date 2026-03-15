"""
Kindred v2.1.0 - Compatibility Matching Engine
8-dimension scoring: personality, values, communication, financial,
attachment, tradeoffs, semantic, dealbreaker.
Match narratives powered by Puter.js on the frontend.
"""

import json
import math
import numpy as np

from app.questions import (
    TRADEOFF_QUESTIONS, VALUES_QUESTIONS, COMMUNICATION_QUESTIONS,
    FINANCIAL_QUESTIONS, ENERGY_QUESTIONS, check_hard_dealbreakers,
)

_model = None

# Default weights (can be overridden per-user)
DEFAULT_WEIGHTS = {
    "personality": 0.20,
    "values": 0.20,
    "communication": 0.12,
    "financial": 0.08,
    "attachment": 0.12,
    "tradeoffs": 0.08,
    "semantic": 0.10,
    "dealbreaker": 0.10,
}


def get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def generate_embedding(text: str) -> np.ndarray:
    model = get_model()
    return model.encode(text, normalize_embeddings=True)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b))


# ---------------------------------------------------------------------------
# Score Recalibration
# ---------------------------------------------------------------------------

def calibrate_score(raw: float) -> float:
    centered = (raw - 0.55) * 5.0
    calibrated = 1.0 / (1.0 + math.exp(-centered))
    return max(0.05, min(0.99, calibrated))


# ---------------------------------------------------------------------------
# Ordered Proximity Scoring (shared by values, communication, financial)
# ---------------------------------------------------------------------------

def _ordered_proximity(opts_a: dict, opts_b: dict, questions: list) -> float:
    """Score similarity based on ordered option proximity."""
    if not opts_a or not opts_b:
        return 0.5
    scores = []
    for q in questions:
        av = opts_a.get(q["id"])
        bv = opts_b.get(q["id"])
        if av is None or bv is None:
            continue
        options = q["options"]
        try:
            ia = options.index(av)
            ib = options.index(bv)
            max_dist = max(len(options) - 1, 1)
            scores.append(1.0 - (abs(ia - ib) / max_dist) ** 1.3)
        except ValueError:
            scores.append(1.0 if av == bv else 0.2)
    return round(sum(scores) / len(scores), 4) if scores else 0.5


# ---------------------------------------------------------------------------
# Dimension Scorers
# ---------------------------------------------------------------------------

def personality_compatibility(a: dict[str, float], b: dict[str, float]) -> float:
    if not a or not b:
        return 0.5

    traits = ["openness", "conscientiousness", "extraversion", "agreeableness", "stability"]
    trait_weights = {
        "openness": 1.0,
        "conscientiousness": 1.3,
        "extraversion": 0.7,
        "agreeableness": 1.3,
        "stability": 1.6,
    }

    weighted_sim = 0.0
    total_weight = 0.0

    for trait in traits:
        av = a.get(trait, 0.5)
        bv = b.get(trait, 0.5)
        w = trait_weights[trait]

        diff = abs(av - bv)
        sim = 1.0 - (diff ** 1.5)

        if trait == "stability":
            avg_val = (av + bv) / 2
            sim = sim * 0.65 + avg_val * 0.35

        if trait in ("conscientiousness", "agreeableness"):
            avg_val = (av + bv) / 2
            sim = sim * 0.75 + avg_val * 0.25

        # Introvert matching: research shows two strong introverts rarely click
        if trait == "extraversion":
            if av < 0.35 and bv < 0.35:
                sim *= 0.85  # Slight penalty, surface coaching instead

        weighted_sim += sim * w
        total_weight += w

    return round(weighted_sim / total_weight, 4)


def values_compatibility(a: dict, b: dict) -> float:
    if not a or not b:
        return 0.5

    scores = []
    ordered_options = {}
    for q in VALUES_QUESTIONS:
        if q["type"] == "choice":
            ordered_options[q["id"]] = q["options"]

    all_keys = set(a.keys()) | set(b.keys())
    for key in all_keys:
        av = a.get(key)
        bv = b.get(key)
        if av is None or bv is None:
            continue

        if isinstance(av, str) and isinstance(bv, str):
            if key in ordered_options:
                opts = ordered_options[key]
                try:
                    ia = opts.index(av)
                    ib = opts.index(bv)
                    max_dist = max(len(opts) - 1, 1)
                    scores.append(1.0 - (abs(ia - ib) / max_dist) ** 1.3)
                except ValueError:
                    scores.append(1.0 if av == bv else 0.2)
            else:
                scores.append(1.0 if av == bv else 0.2)
        elif isinstance(av, (int, float)) and isinstance(bv, (int, float)):
            diff = abs(float(av) - float(bv)) / 4.0
            scores.append(1.0 - diff ** 1.5)

    return round(sum(scores) / len(scores), 4) if scores else 0.5


def communication_compatibility(a: dict, b: dict) -> float:
    """Score communication style alignment using ordered proximity."""
    return _ordered_proximity(a, b, COMMUNICATION_QUESTIONS)


def financial_compatibility(a: dict, b: dict) -> float:
    """Score financial values alignment using ordered proximity."""
    return _ordered_proximity(a, b, FINANCIAL_QUESTIONS)


def tradeoff_compatibility(a: dict, b: dict) -> float:
    if not a or not b:
        return 0.5
    matches = 0
    total = 0
    for to in TRADEOFF_QUESTIONS:
        av = a.get(to["id"])
        bv = b.get(to["id"])
        if av is not None and bv is not None:
            total += 1
            if av == bv:
                matches += 1
    if total == 0:
        return 0.5
    return round(matches / total, 4)


def attachment_compatibility(a: dict[str, float], b: dict[str, float]) -> float:
    if not a or not b:
        return 0.5

    a_secure = a.get("secure", 0.5)
    a_anxious = a.get("anxious", 0.5)
    a_avoidant = a.get("avoidant", 0.5)
    b_secure = b.get("secure", 0.5)
    b_anxious = b.get("anxious", 0.5)
    b_avoidant = b.get("avoidant", 0.5)

    score = (a_secure + b_secure) / 2
    anxious_avoidant = (a_anxious * b_avoidant + a_avoidant * b_anxious) / 2
    score -= anxious_avoidant * 0.5

    if a_secure > 0.6 and b_secure > 0.6:
        score += 0.15
    if a_anxious > 0.6 and b_anxious > 0.6:
        score -= 0.1
    if a_avoidant > 0.6 and b_avoidant > 0.6:
        score -= 0.1

    return round(max(0.0, min(1.0, score)), 4)


def semantic_compatibility(emb_a, emb_b) -> float:
    if emb_a is None or emb_b is None:
        return 0.5
    a_vec = np.frombuffer(emb_a, dtype=np.float32) if isinstance(emb_a, bytes) else np.array(emb_a, dtype=np.float32)
    b_vec = np.frombuffer(emb_b, dtype=np.float32) if isinstance(emb_b, bytes) else np.array(emb_b, dtype=np.float32)
    raw = cosine_similarity(a_vec, b_vec)
    return max(0.0, min(1.0, (raw - 0.2) / 0.6))


def dealbreaker_compatibility(a_breakers: list[str], b_breakers: list[str]) -> float:
    if not a_breakers and not b_breakers:
        return 0.6
    shared = set(a_breakers) & set(b_breakers)
    total = set(a_breakers) | set(b_breakers)
    if not total:
        return 0.6
    return round(0.4 + 0.6 * (len(shared) / len(total)), 4)


# ---------------------------------------------------------------------------
# Energy & Pace Compatibility (used for match ranking bonus)
# ---------------------------------------------------------------------------

def energy_pace_bonus(profile_a: dict, profile_b: dict) -> float:
    """Bonus/penalty for energy level and pace alignment. Not a weighted
    dimension -- applied as a multiplier to final score."""
    bonus = 0.0
    ea = profile_a.get("dating_energy")
    eb = profile_b.get("dating_energy")
    if ea and eb:
        energy_opts = [q["options"] for q in ENERGY_QUESTIONS if q["id"] == "dating_energy"][0]
        try:
            diff = abs(energy_opts.index(ea) - energy_opts.index(eb))
            if diff == 0:
                bonus += 0.03
            elif diff >= 2:
                bonus -= 0.02
        except ValueError:
            pass

    pa = profile_a.get("dating_pace")
    pb = profile_b.get("dating_pace")
    if pa and pb:
        pace_opts = [q["options"] for q in ENERGY_QUESTIONS if q["id"] == "dating_pace"][0]
        try:
            diff = abs(pace_opts.index(pa) - pace_opts.index(pb))
            if diff == 0:
                bonus += 0.02
            elif diff >= 2:
                bonus -= 0.01
        except ValueError:
            pass

    # Intent alignment
    ia = profile_a.get("relationship_intent")
    ib = profile_b.get("relationship_intent")
    if ia and ib:
        intent_opts = [q["options"] for q in ENERGY_QUESTIONS if q["id"] == "relationship_intent"][0]
        try:
            diff = abs(intent_opts.index(ia) - intent_opts.index(ib))
            if diff == 0:
                bonus += 0.03
            elif diff >= 2:
                bonus -= 0.03
        except ValueError:
            pass

    return bonus


# ---------------------------------------------------------------------------
# Coaching Tips (attachment-aware, communication-aware)
# ---------------------------------------------------------------------------

def generate_coaching_tips(profile_a: dict, profile_b: dict, compatibility: dict) -> list[str]:
    """Generate relationship coaching tips based on profile analysis."""
    tips = []
    at_a = profile_a.get("attachment", {})
    at_b = profile_b.get("attachment", {})
    cs_a = profile_a.get("communication_style", {})
    cs_b = profile_b.get("communication_style", {})
    bf_a = profile_a.get("big_five", {})
    bf_b = profile_b.get("big_five", {})

    # Attachment coaching
    if at_a.get("anxious", 0) > 0.6 and at_b.get("avoidant", 0) > 0.5:
        tips.append(f"{profile_b.get('name')} may need more space before responding \u2014 this isn't a sign of disinterest. Give them room to come to you.")
    if at_b.get("anxious", 0) > 0.6 and at_a.get("avoidant", 0) > 0.5:
        tips.append(f"{profile_a.get('name')} may need more space before responding \u2014 this isn't a sign of disinterest. Give them room to come to you.")
    if at_a.get("anxious", 0) > 0.6:
        tips.append(f"{profile_a.get('name')} values reassurance. Regular check-ins and clear communication about feelings go a long way.")
    if at_b.get("anxious", 0) > 0.6:
        tips.append(f"{profile_b.get('name')} values reassurance. Regular check-ins and clear communication about feelings go a long way.")

    # Communication style coaching
    ra = cs_a.get("comm_response")
    rb = cs_b.get("comm_response")
    if ra and rb:
        resp_order = ["Within minutes", "Within a few hours", "Same day", "When I have something meaningful to say"]
        try:
            if abs(resp_order.index(ra) - resp_order.index(rb)) >= 2:
                fast = profile_a.get("name") if resp_order.index(ra) < resp_order.index(rb) else profile_b.get("name")
                slow = profile_b.get("name") if fast == profile_a.get("name") else profile_a.get("name")
                tips.append(f"{fast} responds faster than {slow}. This is just a style difference, not a sign of disinterest.")
        except ValueError:
            pass

    ca = cs_a.get("comm_conflict")
    cb = cs_b.get("comm_conflict")
    if ca and cb and ca != cb:
        tips.append(f"You have different conflict styles ({ca} vs {cb}). Discussing this early helps prevent misunderstandings.")

    # Introvert-introvert coaching
    if bf_a.get("extraversion", 0.5) < 0.35 and bf_b.get("extraversion", 0.5) < 0.35:
        tips.append("You're both introverts \u2014 one of you may need to take the initiative. Try low-pressure conversation starters.")

    return tips[:4]


# ---------------------------------------------------------------------------
# Main Compatibility Function
# ---------------------------------------------------------------------------

def compute_compatibility(profile_a: dict, profile_b: dict,
                          custom_weights: dict | None = None) -> dict:
    conflicts = check_hard_dealbreakers(profile_a, profile_b)
    if conflicts:
        return {
            "total": 0.0,
            "dealbreaker_conflict": True,
            "conflicts": conflicts,
            "breakdown": {k: 0.0 for k in DEFAULT_WEIGHTS},
            "weights": custom_weights or DEFAULT_WEIGHTS,
        }

    weights = dict(DEFAULT_WEIGHTS)
    if custom_weights:
        for k, v in custom_weights.items():
            if k in weights:
                weights[k] = v
        total_w = sum(weights.values())
        if total_w > 0:
            weights = {k: v / total_w for k, v in weights.items()}

    p_score = personality_compatibility(
        profile_a.get("big_five", {}), profile_b.get("big_five", {}))
    v_score = values_compatibility(
        profile_a.get("values", {}), profile_b.get("values", {}))
    cm_score = communication_compatibility(
        profile_a.get("communication_style", {}), profile_b.get("communication_style", {}))
    fn_score = financial_compatibility(
        profile_a.get("financial_values", {}), profile_b.get("financial_values", {}))
    t_score = tradeoff_compatibility(
        profile_a.get("tradeoffs", {}), profile_b.get("tradeoffs", {}))
    at_score = attachment_compatibility(
        profile_a.get("attachment", {}), profile_b.get("attachment", {}))
    s_score = semantic_compatibility(
        profile_a.get("embedding"), profile_b.get("embedding"))
    d_score = dealbreaker_compatibility(
        profile_a.get("dealbreakers", []), profile_b.get("dealbreakers", []))

    raw_total = (
        p_score * weights["personality"]
        + v_score * weights["values"]
        + cm_score * weights["communication"]
        + fn_score * weights["financial"]
        + t_score * weights["tradeoffs"]
        + at_score * weights["attachment"]
        + s_score * weights["semantic"]
        + d_score * weights["dealbreaker"]
    )

    # Apply energy/pace/intent bonus
    ep_bonus = energy_pace_bonus(profile_a, profile_b)
    raw_total = max(0.0, min(1.0, raw_total + ep_bonus))

    calibrated = calibrate_score(raw_total)

    return {
        "total": round(calibrated * 100, 1),
        "raw_total": round(raw_total * 100, 1),
        "dealbreaker_conflict": False,
        "conflicts": [],
        "breakdown": {
            "personality": round(calibrate_score(p_score) * 100, 1),
            "values": round(calibrate_score(v_score) * 100, 1),
            "communication": round(calibrate_score(cm_score) * 100, 1),
            "financial": round(calibrate_score(fn_score) * 100, 1),
            "tradeoffs": round(calibrate_score(t_score) * 100, 1),
            "attachment": round(calibrate_score(at_score) * 100, 1),
            "semantic": round(calibrate_score(s_score) * 100, 1),
            "dealbreakers": round(calibrate_score(d_score) * 100, 1),
        },
        "weights": weights,
    }


def find_matches(target_id: str, profiles: list[dict], top_n: int = 10,
                 custom_weights: dict | None = None) -> list[dict]:
    target = None
    for p in profiles:
        if p["id"] == target_id:
            target = p
            break
    if target is None:
        return []

    target_seeking = target.get("seeking")
    target_gender = target.get("gender")

    results = []
    for p in profiles:
        if p["id"] == target_id:
            continue
        if target_seeking and p.get("gender") != target_seeking:
            continue
        if p.get("seeking") and target_gender != p.get("seeking"):
            continue

        compat = compute_compatibility(target, p, custom_weights)
        results.append({
            "profile_id": p["id"],
            "name": p.get("name", "Unknown"),
            "age": p.get("age"),
            "gender": p.get("gender"),
            "photo": p.get("photo"),
            "verified": p.get("verified", 0),
            "dating_energy": p.get("dating_energy"),
            "relationship_intent": p.get("relationship_intent"),
            "compatibility": compat,
        })

    results.sort(key=lambda x: x["compatibility"]["total"], reverse=True)
    return results[:top_n]


# ---------------------------------------------------------------------------
# Narrative Generation
# ---------------------------------------------------------------------------

def generate_narrative(profile_a: dict, profile_b: dict,
                       compatibility: dict) -> str:
    return _template_narrative(profile_a, profile_b, compatibility)


def _template_narrative(profile_a: dict, profile_b: dict, compatibility: dict) -> str:
    score = compatibility["total"]
    breakdown = compatibility["breakdown"]
    name_a = profile_a.get("name", "Person A")
    name_b = profile_b.get("name", "Person B")
    conflicts = compatibility.get("conflicts", [])

    if conflicts:
        return (
            f"There are fundamental incompatibilities between {name_a} and {name_b}. "
            f"Dealbreaker conflicts detected: {', '.join(conflicts)}. "
            f"These differences represent core values that are unlikely to be reconciled."
        )

    parts = []

    if score >= 80:
        parts.append(f"{name_a} and {name_b} show exceptional compatibility at {score}%.")
    elif score >= 60:
        parts.append(f"{name_a} and {name_b} have solid compatibility at {score}%, with meaningful common ground.")
    elif score >= 40:
        parts.append(f"{name_a} and {name_b} show moderate compatibility at {score}%. There are areas of alignment but also notable differences.")
    else:
        parts.append(f"{name_a} and {name_b} have limited compatibility at {score}%. Significant differences exist across multiple dimensions.")

    best_dim = max(breakdown, key=breakdown.get)
    best_val = breakdown[best_dim]
    dim_labels = {
        "personality": "personality traits",
        "values": "core values and lifestyle",
        "communication": "communication style",
        "financial": "financial values",
        "tradeoffs": "priorities and trade-offs",
        "attachment": "emotional connection style",
        "semantic": "vision for relationships",
        "dealbreakers": "boundaries and standards",
    }
    parts.append(f"Their strongest alignment is in {dim_labels.get(best_dim, best_dim)} ({best_val}%).")

    worst_dim = min(breakdown, key=breakdown.get)
    worst_val = breakdown[worst_dim]
    if worst_val < 50:
        parts.append(f"The biggest gap is in {dim_labels.get(worst_dim, worst_dim)} ({worst_val}%), which could be a source of friction.")

    ll_a = profile_a.get("love_language")
    ll_b = profile_b.get("love_language")
    if ll_a and ll_b:
        if ll_a == ll_b:
            parts.append(f"They share the same love language ({ll_a}), which supports natural emotional reciprocity.")
        else:
            parts.append(f"Their different love languages ({ll_a} vs {ll_b}) will require conscious effort to meet each other's needs.")

    return " ".join(parts)


def generate_icebreakers(profile_a: dict, profile_b: dict, compatibility: dict) -> list[str]:
    icebreakers = []

    vals_a = profile_a.get("values", {})
    vals_b = profile_b.get("values", {})
    for key in vals_a:
        if key in vals_b and vals_a[key] == vals_b[key]:
            if key == "v_lifestyle":
                icebreakers.append(f"You both enjoy '{vals_a[key]}' weekends. What's your favorite way to spend one?")
            elif key == "v_living":
                icebreakers.append(f"You both prefer living in {vals_a[key].lower()} areas. What draws you to that?")

    if profile_a.get("love_language") == profile_b.get("love_language"):
        ll = profile_a["love_language"]
        icebreakers.append(f"You both value {ll}. What does that look like for you in a relationship?")

    # Communication style hooks
    cs_a = profile_a.get("communication_style", {})
    cs_b = profile_b.get("communication_style", {})
    if cs_a.get("comm_conflict") == cs_b.get("comm_conflict"):
        icebreakers.append("You both handle disagreements the same way. How did you develop that approach?")

    # Financial alignment hooks
    fv_a = profile_a.get("financial_values", {})
    fv_b = profile_b.get("financial_values", {})
    if fv_a.get("fin_spending") == fv_b.get("fin_spending"):
        icebreakers.append("You share the same approach to money. What's the best financial decision you've ever made?")

    oe_a = profile_a.get("open_ended", {})
    oe_b = profile_b.get("open_ended", {})
    if oe_a.get("oe2") and oe_b.get("oe2"):
        icebreakers.append("What's the thing you're most passionate about right now?")

    bf_a = profile_a.get("big_five", {})
    bf_b = profile_b.get("big_five", {})
    if bf_a.get("openness", 0) > 0.7 and bf_b.get("openness", 0) > 0.7:
        icebreakers.append("You're both highly open to new experiences. What's the most interesting thing you've tried recently?")
    if bf_a.get("extraversion", 0) < 0.4 and bf_b.get("extraversion", 0) < 0.4:
        icebreakers.append("You both value quiet time. What's your ideal low-key evening?")

    if len(icebreakers) < 3:
        defaults = [
            "What's something people are always surprised to learn about you?",
            "What does a meaningful relationship look like to you?",
            "What's the best advice you've ever received?",
        ]
        for d in defaults:
            if len(icebreakers) >= 3:
                break
            if d not in icebreakers:
                icebreakers.append(d)

    return icebreakers[:5]
