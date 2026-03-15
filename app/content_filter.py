"""
Kindred v2.1.0 - Content Filtering
Basic profanity/spam detection for messages and profiles.
"""

import re

from app.config import CONTENT_FILTER_ENABLED

# Common profanity/slur patterns (kept minimal, extend as needed)
_BLOCKED_PATTERNS = [
    r"\b(fuck|shit|cunt|nigger|faggot|retard)\w*\b",
]

# Spam patterns
_SPAM_PATTERNS = [
    r"(https?://\S+){3,}",  # 3+ URLs in one message
    r"(.)\1{9,}",  # Same char repeated 10+ times
    r"\b(buy now|click here|free money|act now|limited offer)\b",
    r"(dm me on|follow me on|add me on)\s*(snap|insta|telegram|whatsapp)",
]

_blocked_re = [re.compile(p, re.IGNORECASE) for p in _BLOCKED_PATTERNS]
_spam_re = [re.compile(p, re.IGNORECASE) for p in _SPAM_PATTERNS]


def check_content(text: str) -> dict:
    """
    Check text for profanity and spam.
    Returns {"clean": True} or {"clean": False, "reason": str, "type": str}.
    """
    if not CONTENT_FILTER_ENABLED or not text:
        return {"clean": True}

    text = text[:10000]

    for pattern in _blocked_re:
        match = pattern.search(text)
        if match:
            return {
                "clean": False,
                "reason": "Contains inappropriate language",
                "type": "profanity",
                "matched": match.group(),
            }

    for pattern in _spam_re:
        match = pattern.search(text)
        if match:
            return {
                "clean": False,
                "reason": "Detected as spam",
                "type": "spam",
                "matched": match.group(),
            }

    return {"clean": True}


def filter_message(text: str) -> tuple[str, bool]:
    """
    Returns (filtered_text, was_filtered).
    Replaces profanity with asterisks rather than blocking entirely.
    """
    if not CONTENT_FILTER_ENABLED or not text:
        return text, False

    text = text[:10000]
    filtered = text
    was_filtered = False

    for pattern in _blocked_re:
        def _censor(m):
            word = m.group()
            return word[0] + "*" * (len(word) - 1)
        new_text = pattern.sub(_censor, filtered)
        if new_text != filtered:
            was_filtered = True
            filtered = new_text

    return filtered, was_filtered
