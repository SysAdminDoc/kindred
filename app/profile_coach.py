"""Private, deterministic profile-writing feedback.

The coach deliberately uses a small local language heuristic instead of a
remote generative service. It gives users actionable feedback about clarity,
specificity, warmth, and low-stakes vulnerability without retaining or
shipping their profile text anywhere.
"""

from __future__ import annotations

import re


COACH_VERSION = "kindred-local-profile-coach-v1"
_WORD_RE = re.compile(r"\b[\w’'-]+\b", re.UNICODE)
_SENTENCE_RE = re.compile(r"[^.!?]+(?:[.!?]+|$)")
_VAGUE_PHRASES = (
    "just ask",
    "love to laugh",
    "love having fun",
    "work hard play hard",
    "partner in crime",
    "live laugh love",
    "no drama",
)
_CONCRETE_TERMS = {
    "art", "beach", "bicycle", "book", "books", "brew", "coffee", "cook",
    "cooking", "dance", "dog", "dogs", "garden", "hike", "hiking", "jazz",
    "museum", "music", "pasta", "photography", "read", "reading", "run",
    "running", "salsa", "travel", "traveling", "trail", "volunteer", "walk",
    "weekend", "write", "writing",
}
_WARMTH_TERMS = {
    "care", "caring", "curious", "delight", "enjoy", "favorite", "grateful",
    "kind", "laugh", "listen", "love", "notice", "playful", "thoughtful",
    "warm", "wonder", "wonderful",
}
_VULNERABILITY_TERMS = {
    "admit", "learning", "mistake", "nervous", "proud", "trying", "working",
    "hope", "feel", "feeling", "growing", "important", "imperfect", "honest",
    "grateful", "curious",
}


def _words(text: str) -> list[str]:
    return [match.group(0).lower() for match in _WORD_RE.finditer(text or "")]


def _clamp_score(value: float) -> int:
    return max(0, min(100, round(value)))


def _score_length(word_count: int, low: int, high: int) -> int:
    if word_count <= 0:
        return 0
    if low <= word_count <= high:
        return 100
    if word_count < low:
        return _clamp_score(100 * word_count / low)
    return _clamp_score(100 - min(60, (word_count - high) * 1.5))


def _dimension(key: str, label: str, score: int, summary: str) -> dict:
    return {"key": key, "label": label, "score": score, "summary": summary}


def coach_profile(profile: dict) -> dict:
    """Return local writing feedback for one profile without storing its text."""
    headline = str(profile.get("headline") or "").strip()
    about = str(profile.get("about_me") or "").strip()
    interests = str(profile.get("interests") or "").strip()
    combined = " ".join(part for part in (headline, about, interests) if part)
    words = _words(combined)
    about_words = _words(about)
    sentences = [part.strip() for part in _SENTENCE_RE.findall(about) if part.strip()]
    lowered = combined.lower()
    unique_words = len(set(words))
    first_person = sum(word in {"i", "i’m", "i've", "my", "me", "we", "our"} for word in words)
    concrete_hits = len(set(words) & _CONCRETE_TERMS)
    warmth_hits = len(set(words) & _WARMTH_TERMS)
    vulnerability_hits = len(set(words) & _VULNERABILITY_TERMS)
    vague_hits = sum(phrase in lowered for phrase in _VAGUE_PHRASES)

    headline_score = _score_length(len(_words(headline)), 4, 12)
    if vague_hits and headline:
        headline_score -= min(30, vague_hits * 10)
    clarity_score = _clamp_score(
        _score_length(len(about_words), 45, 170)
        + (15 if 2 <= len(sentences) <= 6 else 0)
        - (20 if len(sentences) == 1 and len(about_words) > 70 else 0)
        - min(25, vague_hits * 8)
    )
    specificity_score = _clamp_score(
        (min(5, concrete_hits) / 5 * 65)
        + (20 if first_person else 0)
        + (15 if interests else 0)
    )
    warmth_score = _clamp_score(
        min(5, warmth_hits) / 5 * 65
        + (20 if first_person else 0)
        + (15 if len(about_words) >= 35 else 0)
    )
    vulnerability_score = _clamp_score(
        min(4, vulnerability_hits) / 4 * 75
        + (25 if any(marker in lowered for marker in ("i feel", "i'm learning", "i am learning")) else 0)
    )
    overall = _clamp_score(
        headline_score * 0.15
        + clarity_score * 0.35
        + specificity_score * 0.25
        + warmth_score * 0.15
        + vulnerability_score * 0.10
    )

    strengths: list[str] = []
    suggestions: list[dict] = []
    if headline_score >= 75:
        strengths.append("Your headline gives people a quick reason to keep reading.")
    if specificity_score >= 65:
        strengths.append("You include concrete details that make your profile memorable.")
    if warmth_score >= 65:
        strengths.append("Your writing has a welcoming, human tone.")
    if vulnerability_score >= 60:
        strengths.append("You share a bit of honest context without needing to overshare.")

    if not headline:
        suggestions.append({
            "field": "headline",
            "priority": "high",
            "title": "Add a specific headline",
            "detail": "Give someone one concrete hook they can ask you about.",
            "example": "Weekend trail walks, ambitious pasta experiments, and good questions",
        })
    elif headline_score < 60:
        suggestions.append({
            "field": "headline",
            "priority": "medium",
            "title": "Make the headline more distinctive",
            "detail": "Swap broad claims for one activity, value, or small detail that sounds like you.",
            "example": "Learning salsa badly, enthusiastically, and on purpose",
        })
    if not about:
        suggestions.append({
            "field": "about_me",
            "priority": "high",
            "title": "Write a short About Me",
            "detail": "Aim for two or three sentences: what energizes you, what you care about, and what a good day looks like.",
            "example": "I reset with a long walk and a new recipe. I care about staying curious and making room for people to be themselves.",
        })
    elif len(about_words) < 35:
        suggestions.append({
            "field": "about_me",
            "priority": "medium",
            "title": "Add one more small scene",
            "detail": "Your bio is easy to scan; one specific moment or ritual would give a future match an opening question.",
            "example": "My ideal Sunday starts with a farmers’ market and ends with a movie I can quote badly.",
        })
    elif len(about_words) > 190:
        suggestions.append({
            "field": "about_me",
            "priority": "medium",
            "title": "Trim the longest paragraph",
            "detail": "Keep the most revealing details and remove repeated adjectives so the main thread is easier to follow.",
            "example": "Choose the two details that best show how you spend time and what you value.",
        })
    if specificity_score < 55 and about:
        suggestions.append({
            "field": "about_me",
            "priority": "high",
            "title": "Replace generalities with one example",
            "detail": "Words like fun or adventurous are hard to respond to on their own. Name a place, ritual, project, or recent curiosity.",
            "example": "Instead of ‘I love adventure,’ try ‘I plan one unfamiliar day trip each month.’",
        })
    if vulnerability_score < 45 and about:
        suggestions.append({
            "field": "about_me",
            "priority": "low",
            "title": "Add a low-stakes honest detail",
            "detail": "A small truth about what you are learning or working on can make the profile feel more open; keep sensitive information private.",
            "example": "I’m learning to ask for help before I’m already overwhelmed.",
        })
    if not interests:
        suggestions.append({
            "field": "interests",
            "priority": "medium",
            "title": "Add a few conversation seeds",
            "detail": "List three to five interests with at least one unusual or current one.",
            "example": "Public gardens, speculative fiction, ramen maps, and beginner pottery",
        })

    if unique_words >= 20 and not strengths:
        strengths.append("Your profile has enough variety for a coachable first draft.")
    if not strengths:
        strengths.append("You have a clear starting point; a few specific details will do most of the work.")

    return {
        "model": COACH_VERSION,
        "local_only": True,
        "overall_score": overall,
        "dimensions": [
            _dimension("clarity", "Clarity", clarity_score, "How easy the profile is to scan and understand."),
            _dimension("specificity", "Specificity", specificity_score, "How many concrete openings it gives a reader."),
            _dimension("warmth", "Warmth", warmth_score, "How welcoming and personal the language feels."),
            _dimension("vulnerability", "Vulnerability", vulnerability_score, "Whether it shares a low-stakes honest detail."),
        ],
        "strengths": strengths[:4],
        "suggestions": suggestions[:6],
        "stats": {
            "headline_words": len(_words(headline)),
            "about_words": len(about_words),
            "about_sentences": len(sentences),
            "interest_words": len(_words(interests)),
        },
    }
