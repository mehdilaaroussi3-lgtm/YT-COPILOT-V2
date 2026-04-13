"""Video idea generator.

Given a channel profile + optional topic direction, asks Gemini text to produce
6 original video ideas grounded in the channel's niche and recent outliers.
Uses outlier titles from the SQLite DB as creative fuel so ideas stay anchored
in what's actually performing on YouTube right now.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import uuid

from core.profile_loader import load_profile
from data.db import db
from generators.gemini_text import generate_text


IDEA_PROMPT = """\
You are generating YouTube video ideas for a faceless channel.

CHANNEL PROFILE:
- Name: {channel_name}
- Niche: {niche}
- Preferred tone: {tone}
- Avoid: {avoid}

{topic_block}
{outlier_block}

Task: generate {count} ORIGINAL video ideas. Each idea must:
- Match the channel's niche and tone
- Create a strong curiosity gap (the viewer needs to click to resolve)
- Be visually thumbnail-friendly (you can imagine a dramatic visual for it)
- Be distinct from the others in this batch

Output STRICT JSON only — an array of {count} objects, no prose, no fence:

[
  {{
    "title": "<working video title, 3-8 words>",
    "description": "<1-2 sentence pitch of what this video covers and the hook>",
    "angle": "<why this idea works for this channel in 1 line>"
  }},
  ...
]
"""


def _recent_outlier_titles(niche: str, limit: int = 20,
                              channel_id: str | None = None) -> list[str]:
    d = db()
    if channel_id:
        sql = """
        SELECT title FROM videos
        WHERE channel_id = ? AND outlier_score >= 1
        ORDER BY outlier_score DESC
        LIMIT ?
        """
        return [r["title"] for r in d.query(sql, [channel_id, limit]) if r.get("title")]
    sql = """
    SELECT v.title FROM videos v
    LEFT JOIN channels c ON c.channel_id = v.channel_id
    WHERE (c.niche = ? OR c.niche IS NULL)
      AND v.outlier_score >= 2
    ORDER BY v.outlier_score DESC
    LIMIT ?
    """
    return [r["title"] for r in d.query(sql, [niche, limit]) if r.get("title")]


def generate_ideas(channel: str, topic: str | None = None,
                    count: int = 6) -> list[dict]:
    """Generate + persist `count` video ideas for a channel."""
    profile = load_profile(channel)
    niche = profile.get("niche", "documentary_essay")

    tone = ", ".join(profile.get("content_style", {}).get("preferred_compositions", [])) or "editorial"
    avoid = ", ".join(profile.get("content_style", {}).get("avoid", [])) or "generic"

    topic_block = f"TOPIC DIRECTION: {topic}\n" if topic else ""
    outliers = _recent_outlier_titles(niche, channel_id=profile.get("channel_id"))
    outlier_block = ""
    if outliers:
        outlier_block = (
            "REFERENCE OUTLIERS (titles that hugely outperformed in this niche — "
            "emulate their energy, DO NOT copy):\n"
            + "\n".join(f"- {t}" for t in outliers[:15])
            + "\n"
        )

    prompt = IDEA_PROMPT.format(
        channel_name=profile.get("name", channel),
        niche=niche,
        tone=tone, avoid=avoid,
        topic_block=topic_block,
        outlier_block=outlier_block,
        count=count,
    )

    raw = generate_text(prompt, temperature=0.85)
    items = _parse_json_array(raw)
    batch_id = uuid.uuid4().hex[:12]
    now = dt.datetime.now(dt.UTC).isoformat()

    persisted = []
    d = db()
    for item in items[:count]:
        row = {
            "channel": channel,
            "topic": topic or "",
            "idea_title": (item.get("title") or "").strip(),
            "idea_description": (item.get("description") or "").strip(),
            "created_at": now,
            "batch_id": batch_id,
        }
        d["generated_ideas"].insert(row, alter=True)
        # Attach angle + assigned id for the UI
        persisted.append({
            **row,
            "angle": (item.get("angle") or "").strip(),
            "id": d["generated_ideas"].last_pk,
        })
    return persisted


def history(channel: str | None = None, limit: int = 50) -> list[dict]:
    """Return recent ideas grouped by batch_id → date."""
    d = db()
    if channel:
        rows = list(d["generated_ideas"].rows_where(
            "channel = ?", [channel],
            order_by="created_at desc",
            limit=limit,
        ))
    else:
        rows = list(d["generated_ideas"].rows_where(
            order_by="created_at desc", limit=limit,
        ))
    return rows


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
