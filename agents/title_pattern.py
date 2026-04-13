"""Title Pattern Agent (masterplan §25.4).

Extracts recurring title FORMULAS from outlier videos in a niche.
Examples it detects:
  - "The [ADJ] [NOUN] That [SHOCKING VERB]"
  - "Why [AUTHORITY] Is [NEGATIVE ACTION]"
  - "I [PAST VERB] [BIG NUMBER] [THING]"
"""
from __future__ import annotations

import datetime as dt
import json

from data.db import db
from generators.gemini_text import generate_text


PATTERN_PROMPT = """\
Below are titles from {n} TOP OUTLIER YouTube videos in the {niche} niche.
These videos massively outperformed their channel average (5x+ scores).

TITLES:
{titles}

Extract the 5 RECURRING TITLE FORMULAS that appear most often. For each:
1. The formula in template form (e.g. "Why [AUTHORITY] Is [NEGATIVE ACTION]")
2. How many of the titles match it
3. Two or three example titles from the list above

Output STRICT JSON only:
[
  {{"pattern": "...", "frequency": 0, "examples": ["...", "..."]}},
  ...
]
"""


class TitlePatternAgent:
    def __init__(self) -> None:
        self.db = db()

    def extract_patterns(self, niche: str, min_outlier_score: float = 5.0,
                          limit: int = 50) -> list[dict]:
        titles = [
            r["title"] for r in self.db["videos"].rows_where(
                "outlier_score >= ?", [min_outlier_score], order_by="outlier_score desc",
                limit=limit,
            )
            if r.get("title")
        ]
        if not titles:
            return []

        prompt = PATTERN_PROMPT.format(
            n=len(titles), niche=niche,
            titles="\n".join(f"- {t}" for t in titles),
        )
        raw = generate_text(prompt, temperature=0.3)
        if raw.startswith("```"):
            raw = raw.strip("`").lstrip("json").strip()
        try:
            patterns = json.loads(raw)
        except json.JSONDecodeError:
            return []

        # Persist
        self.db["title_patterns"].delete_where("niche = ?", [niche])
        for p in patterns:
            self.db["title_patterns"].insert({
                "niche": niche,
                "pattern": p.get("pattern", ""),
                "frequency": int(p.get("frequency", 0)),
                "avg_outlier_score": 0.0,
                "examples": json.dumps(p.get("examples", [])),
            }, alter=True)
        return patterns
