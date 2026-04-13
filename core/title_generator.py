"""Title variation generator.

Given a channel + a video idea (or working title), produces 6 click-optimized
title variants applying the §24.4 data-backed rules:
- 5-word / ≤30-char sweet spot
- negative sentiment / threat framing (+22% views)
- high readability, no gratuitous numbers
- distinct emotional angles across the 6 variants (curiosity / fear / anger / joy / mystery / authority)
"""
from __future__ import annotations

import datetime as dt
import json
import re
import uuid

from core.profile_loader import load_profile
from data.db import db
from generators.gemini_text import generate_text


TITLE_PROMPT = """\
You are a YouTube packaging expert writing title variations.

CHANNEL: {channel} ({niche})
VIDEO IDEA / WORKING TITLE:
"{idea}"

Generate {count} DISTINCT title variants. Apply these rules from a 300K-video /
62B-views study:
- Target 5 words / ≤30 characters where possible
- Negative framing beats positive (+22% views): "Why X is failing" > "How to grow X"
- High readability — short words, spoken language, minimal punctuation
- Numbers HURT click-through by ~11% in titles — use them sparingly
- Each of the {count} variants must use a different emotional angle:
  1. curiosity gap  2. loss / threat  3. anger / injustice  4. authority reveal
  5. mystery  6. contrarian claim

Output STRICT JSON only — an array of {count} objects:

[
  {{"title": "...", "angle": "curiosity"}},
  {{"title": "...", "angle": "threat"}},
  ...
]

No prose, no markdown fence.
"""


def generate_titles(channel: str, idea: str, count: int = 6) -> list[dict]:
    profile = load_profile(channel)
    niche = profile.get("niche", "documentary_essay")

    prompt = TITLE_PROMPT.format(
        channel=profile.get("name", channel),
        niche=niche, idea=idea.strip(), count=count,
    )
    raw = generate_text(prompt, temperature=0.8)
    items = _parse_json_array(raw)

    batch_id = uuid.uuid4().hex[:12]
    now = dt.datetime.now(dt.UTC).isoformat()
    d = db()

    persisted = []
    for item in items[:count]:
        title = (item.get("title") or "").strip()
        if not title:
            continue
        row = {
            "channel": channel,
            "source_idea": idea.strip(),
            "title": title,
            "char_count": len(title),
            "created_at": now,
            "batch_id": batch_id,
            "pinned": 0,
        }
        d["generated_titles"].insert(row, alter=True)
        persisted.append({
            **row,
            "angle": (item.get("angle") or "").strip(),
            "id": d["generated_titles"].last_pk,
        })
    return persisted


def history(channel: str | None = None, limit: int = 60) -> list[dict]:
    d = db()
    if channel:
        return list(d["generated_titles"].rows_where(
            "channel = ?", [channel],
            order_by="created_at desc", limit=limit,
        ))
    return list(d["generated_titles"].rows_where(
        order_by="created_at desc", limit=limit,
    ))


def toggle_pin(title_id: int) -> bool:
    d = db()
    row = d["generated_titles"].get(title_id)
    new_val = 0 if row.get("pinned") else 1
    d["generated_titles"].update(title_id, {"pinned": new_val})
    return bool(new_val)


def _parse_json_array(text: str) -> list[dict]:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\[.*\]", text, re.DOTALL)
        if not m:
            return []
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            return []
