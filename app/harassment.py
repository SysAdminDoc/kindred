"""Small, explainable harassment signal detector for direct messages.

This is intentionally a conservative signal layer rather than a generalized
moderation model.  It scores direct threats, coercive sexual language, slurs,
and targeted abuse; the caller combines that score with recent events for the
same sender/recipient pair to decide whether to warn or auto-mute.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class HarassmentSignal:
    score: int
    categories: tuple[str, ...]

    @property
    def flagged(self) -> bool:
        return self.score > 0


@dataclass(frozen=True)
class HarassmentDecision:
    signal: HarassmentSignal
    previous_score: int
    previous_count: int
    window_score: int
    window_count: int
    action: str

    @property
    def reason(self) -> str:
        return ",".join(self.signal.categories) or "pattern"


_THREAT_PATTERNS = (
    re.compile(r"\b(?:i(?:'| wi| a)?ll|gonna|going to)\s+(?:kill|hurt|find|attack|rape)\b", re.I),
    re.compile(r"\b(?:you deserve to|go)\s+(?:die|kill yourself)\b", re.I),
    re.compile(r"\b(?:come|show up)\s+to\s+(?:your|ur)\s+(?:house|home|work)\b", re.I),
)
_COERCION_PATTERNS = (
    re.compile(r"\b(?:send|show)\s+(?:me\s+)?(?:nudes?|pics?|pictures?)\b", re.I),
    re.compile(r"\b(?:if you don't|unless you)\s+.*\b(?:expose|post|share)\b", re.I),
)
_SLUR_PATTERN = re.compile(r"\b(?:nigger|faggot|retard|tranny|kike|spic)\w*\b", re.I)
_TARGETED_ABUSE_PATTERNS = (
    re.compile(
        r"\b(?:you(?:'re| are)|ur)\s+(?:an?\s+)?(?:idiot|moron|loser|worthless|ugly|stupid|disgusting|pathetic)\b",
        re.I,
    ),
    re.compile(r"\b(?:shut up|go away|nobody wants you|you suck)\b", re.I),
)


def _normalize(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text or "")
    normalized = normalized.replace("\u200b", " ")
    return re.sub(r"\s+", " ", normalized).strip()


def analyze_message(text: str) -> HarassmentSignal:
    """Return a bounded signal without retaining the message text."""
    normalized = _normalize(text)[:10000]
    if not normalized:
        return HarassmentSignal(0, ())

    categories: list[str] = []
    score = 0
    if any(pattern.search(normalized) for pattern in _THREAT_PATTERNS):
        categories.append("threat")
        score += 4
    if any(pattern.search(normalized) for pattern in _COERCION_PATTERNS):
        categories.append("sexual_coercion")
        score += 3
    if _SLUR_PATTERN.search(normalized):
        categories.append("slur")
        score += 3
    if any(pattern.search(normalized) for pattern in _TARGETED_ABUSE_PATTERNS):
        categories.append("targeted_abuse")
        score += 1
    return HarassmentSignal(min(score, 5), tuple(categories))


def decide(
    signal: HarassmentSignal,
    previous_score: int,
    previous_count: int,
    *,
    warn_score: int = 2,
    mute_score: int = 4,
) -> HarassmentDecision:
    """Combine the current signal with the pair's sliding-window history."""
    window_score = max(0, previous_score) + signal.score
    window_count = max(0, previous_count) + (1 if signal.flagged else 0)
    if not signal.flagged:
        action = "clean"
    elif window_score >= max(1, mute_score):
        action = "auto_mute"
    elif window_score >= max(1, warn_score):
        action = "warn"
    else:
        action = "flagged"
    return HarassmentDecision(
        signal=signal,
        previous_score=max(0, previous_score),
        previous_count=max(0, previous_count),
        window_score=window_score,
        window_count=window_count,
        action=action,
    )
