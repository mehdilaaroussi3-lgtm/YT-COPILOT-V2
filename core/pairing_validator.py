"""Thumbnail-title pairing validator (masterplan §24.5).

A thumbnail that repeats title words wastes the click opportunity. This validator
checks redundancy and suggests COMPLEMENTARY hooks.
"""
from __future__ import annotations

from dataclasses import dataclass

STOP = {"the", "a", "an", "of", "in", "on", "at", "to", "for", "and", "or",
        "is", "are", "was", "were", "be", "this", "that", "with"}


@dataclass
class PairingReport:
    title: str
    hook: str
    overlap: list[str]
    score: int          # 0-10 (10 = excellent complementarity)
    issues: list[str]
    is_acceptable: bool


def validate_pairing(title: str, hook: str) -> PairingReport:
    title_words = {w.lower().strip(".,!?;:'\"$") for w in title.split()
                   if w.lower() not in STOP}
    hook_words = {w.lower().strip(".,!?;:'\"$") for w in hook.split()
                  if w.lower() not in STOP}
    overlap = sorted(title_words & hook_words)

    issues = []
    score = 10

    overlap_ratio = len(overlap) / max(len(hook_words), 1)
    if overlap_ratio >= 0.6:
        issues.append(f"Hook repeats {len(overlap)} of {len(hook_words)} title words "
                      f"({int(overlap_ratio*100)}% overlap). Pick a complementary fragment.")
        score -= 5
    elif overlap_ratio >= 0.3:
        issues.append(f"Hook overlaps title by {int(overlap_ratio*100)}% — consider trimming.")
        score -= 2

    if len(hook.split()) > 5:
        issues.append("Hook is too long (>5 words). Trim to 2-5 words.")
        score -= 2
    if len(hook) > 25:
        issues.append("Hook char count > 25. Mobile readability suffers.")
        score -= 1

    return PairingReport(
        title=title, hook=hook, overlap=overlap, score=max(0, score),
        issues=issues, is_acceptable=score >= 6,
    )
