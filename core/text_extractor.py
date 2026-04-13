"""Extract a 3-5 word thumbnail text hook from a video title.

Rules from masterplan §19:
- numbers + dollar signs always survive
- max 5 words, min 2
- always uppercase
- shock words preserved
- output COMPLEMENTS the title (curiosity gap), doesn't repeat it
"""
from __future__ import annotations

from core.analyzer import SHOCK_WORDS, TitleAnalysis, analyze_title

STOPWORDS = {"the", "a", "an", "of", "in", "on", "at", "to", "for", "and", "or",
             "but", "is", "are", "was", "were", "be", "been", "being", "have",
             "has", "had", "do", "does", "did", "will", "would", "could",
             "should", "may", "might", "must", "shall", "can", "this", "that",
             "these", "those", "i", "you", "he", "she", "it", "we", "they",
             "with", "as", "by", "from", "about"}


def extract_hook(title: str, max_words: int = 4) -> str:
    """Return UPPERCASE 2-4 word hook prioritizing money / numbers / shock words."""
    a = analyze_title(title)

    # Priority 1: money
    if a.money:
        money_token = a.money[0].replace(" ", "").upper()
        # If only money, pad with one shock word or noun
        rest = _pick_keywords(a, exclude=[money_token], n=max_words - 1)
        return f"{money_token} {' '.join(rest)}".strip().upper()

    # Priority 2: numbers
    if a.numbers:
        num = a.numbers[0]
        rest = _pick_keywords(a, exclude=[num], n=max_words - 1)
        return f"{num} {' '.join(rest)}".strip().upper()

    # Priority 3: shock words from title
    if a.shock_words:
        shock = a.shock_words[0].upper()
        return shock

    # Priority 4: derived punchy word based on sentiment / question form
    t_low = title.lower()
    if t_low.startswith("why"):
        return "WHY?"
    if t_low.startswith("how"):
        return "HOW?"
    if a.sentiment == "negative":
        return "EXPOSED"
    if "first" in t_low or "new" in t_low or "just" in t_low:
        return "REVEALED"
    return "INSIDE"


def _pick_keywords(a: TitleAnalysis, exclude: list[str], n: int) -> list[str]:
    excl = {e.lower().strip("$,") for e in exclude}
    out = []
    for w in a.title.split():
        clean = w.lower().strip(".,!?;:'\"")
        if clean in STOPWORDS or clean in excl or len(clean) < 2:
            continue
        out.append(w.upper())
        if len(out) >= n:
            break
    return out


def suggest_alternatives(title: str) -> list[str]:
    """Three text options for the user to pick from."""
    a = analyze_title(title)
    options = []

    # Number-focused
    if a.money or a.numbers:
        options.append(extract_hook(title))

    # Emotion/shock-focused
    if a.shock_words:
        options.append(a.shock_words[0].upper())
    elif a.sentiment == "negative":
        options.append("EXPOSED")

    # Question hook
    if title.lower().startswith(("why", "how", "what")):
        options.append("HOW?")

    # Dedupe + cap
    seen = set()
    unique = []
    for o in options + [extract_hook(title)]:
        if o and o not in seen:
            seen.add(o); unique.append(o)
    return unique[:3]
