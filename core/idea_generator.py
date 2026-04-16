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
Generate {count} new YouTube video ideas for the channel {channel_handle} ({channel_name}).

Here are real past video titles from this channel so you understand what it's about. Study them to infer the subject matter, characters, themes, vocabulary, and world this channel covers:

{channel_titles_block}

{topic_block}Rules for the ideas:
- Stay in the SAME topic domain as the real titles above. If they are about Game of Thrones, write more Game of Thrones ideas. If about legal loopholes and financial exploits, write more in that world. Never drift into generic "interesting story" territory just because of the niche label "{niche}".
- Don't repeat what this channel has already covered.
- Each idea must be distinct from the others.
- Strong curiosity gap. Visually thumbnail-friendly.
- Title: 3 to 8 words, matching this channel's phrasing style.
- Description: 1-2 sentences, what the video covers and its hook.
- Angle: one line on why this specific idea fits this specific channel's audience.

For inspiration on viral energy/structure (not topic), here are unrelated outlier titles from similar-niche channels:
{outlier_block}

Output a STRICT JSON array of {count} objects, each with keys "title", "description", "angle". No prose, no markdown fence, no extra keys. Example shape:
[{{"title": "...", "description": "...", "angle": "..."}}]
"""


def _sanitize_title(s: str) -> str:
    """Strip bytes that corrupt the Gemini prompt stream.

    Some scraped titles contain mojibake replacement chars (\\ufffd) or raw
    non-UTF-8 bytes — these truncate the request body mid-transit and the
    model sees a cut-off message. Replace them with a safe placeholder and
    re-encode clean."""
    if not s:
        return ""
    # Drop replacement chars entirely (they're already-broken data)
    s = s.replace("\ufffd", "")
    # Re-encode with aggressive fallback to kill any lingering surrogates
    s = s.encode("utf-8", errors="ignore").decode("utf-8", errors="ignore")
    return s.strip()


def _channel_real_titles(channel_id: str | None, limit: int = 20) -> list[str]:
    """All of this channel's real past video titles — the single most important
    signal for what topic domain to stay in. No outlier filter: we want a
    BROAD view of the channel's content, not only the viral hits. Titles
    are sanitized so non-UTF-8 mojibake bytes don't break the prompt."""
    if not channel_id:
        return []
    d = db()
    try:
        rows = list(d["videos"].rows_where(
            "channel_id = ?", [channel_id],
            order_by="outlier_score desc, published_at desc",
            limit=limit,
        ))
        out = []
        for r in rows:
            t = _sanitize_title(r.get("title", ""))
            if t:
                out.append(t)
        return out
    except Exception:  # noqa: BLE001
        return []


def _recent_outlier_titles(niche: str, limit: int = 20,
                              channel_id: str | None = None) -> list[str]:
    """Outlier titles from OTHER channels in the same niche — used only as
    'energy reference', never as the primary domain signal."""
    d = db()
    sql = """
    SELECT v.title FROM videos v
    LEFT JOIN channels c ON c.channel_id = v.channel_id
    WHERE (c.niche = ? OR c.niche IS NULL)
      AND v.outlier_score >= 2
      AND v.channel_id != ?
    ORDER BY v.outlier_score DESC
    LIMIT ?
    """
    out = []
    for r in d.query(sql, [niche, channel_id or "", limit]):
        t = _sanitize_title(r.get("title", ""))
        if t:
            out.append(t)
    return out


def generate_ideas(channel: str, topic: str | None = None,
                    count: int = 6) -> list[dict]:
    """Generate + persist `count` video ideas for a channel.

    Anchors the model in the channel's REAL past video titles (the single
    strongest domain signal) so ideas stay inside the channel's actual topic
    world — not some generic 'documentary essay' space.
    """
    profile = load_profile(channel)
    niche = profile.get("niche", "documentary_essay")
    channel_id = profile.get("channel_id") or (channel if isinstance(channel, str) and channel.startswith("UC") else None)

    # If the channel wasn't scanned yet (no real titles cached), trigger a
    # scan synchronously — otherwise we'd be prompting blind and get the
    # generic-story failure mode the user just hit.
    real_titles = _channel_real_titles(channel_id, limit=20)
    if not real_titles and channel_id:
        try:
            from core.style_channel import resolve_style_channel
            resolve_style_channel(channel_id)
            real_titles = _channel_real_titles(channel_id, limit=20)
        except Exception:  # noqa: BLE001
            real_titles = []

    if real_titles:
        channel_titles_block = "\n".join(f"- {t}" for t in real_titles)
    else:
        channel_titles_block = (
            "(No past titles cached for this channel yet — infer the topic "
            "domain from the channel handle and niche label alone.)"
        )

    topic_block = f"TOPIC DIRECTION: {topic}\n" if topic else ""
    outliers = _recent_outlier_titles(niche, channel_id=channel_id)
    outlier_block = ""
    if outliers:
        outlier_block = (
            "(These come from OTHER channels in a similar niche — borrow "
            "their ENERGY / structure only. They are NOT the topic domain.)\n"
            + "\n".join(f"- {t}" for t in outliers[:10])
            + "\n"
        )
    else:
        outlier_block = "(none available)\n"

    handle = profile.get("handle") or ""
    if handle and not handle.startswith("@"):
        handle = "@" + handle

    prompt = IDEA_PROMPT.format(
        channel_handle=handle or "(unknown handle)",
        channel_name=profile.get("name", channel),
        niche=niche,
        channel_titles_block=channel_titles_block,
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


def generate_ideas_for_channel(channel_ctx: dict, topic: str | None = None,
                               count: int = 6) -> list[dict]:
    """Generate ideas using a pre-built channel_ctx dict (no profile_loader).

    channel_ctx keys:
      name, niche, reference_channel_id, reference_channel_name, tone
    """
    niche = channel_ctx.get("niche") or "documentary_essay"
    channel_id = channel_ctx.get("reference_channel_id") or None
    channel_name = channel_ctx.get("name") or ""

    real_titles = _channel_real_titles(channel_id, limit=20)

    if real_titles:
        channel_titles_block = "\n".join(f"- {t}" for t in real_titles)
    else:
        channel_titles_block = (
            "(No past titles cached for this channel yet — infer the topic "
            "domain from the channel name and niche label alone.)"
        )

    topic_block = f"TOPIC DIRECTION: {topic}\n" if topic else ""
    outliers = _recent_outlier_titles(niche, channel_id=channel_id)
    outlier_block = ""
    if outliers:
        outlier_block = (
            "(These come from OTHER channels in a similar niche — borrow "
            "their ENERGY / structure only. They are NOT the topic domain.)\n"
            + "\n".join(f"- {t}" for t in outliers[:10])
            + "\n"
        )
    else:
        outlier_block = "(none available)\n"

    handle = channel_ctx.get("reference_channel_name") or channel_name
    if handle and not handle.startswith("@"):
        handle = "@" + handle

    prompt = IDEA_PROMPT.format(
        channel_handle=handle or "(unknown handle)",
        channel_name=channel_name,
        niche=niche,
        channel_titles_block=channel_titles_block,
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
            "channel": channel_name,
            "topic": topic or "",
            "idea_title": (item.get("title") or "").strip(),
            "idea_description": (item.get("description") or "").strip(),
            "created_at": now,
            "batch_id": batch_id,
        }
        d["generated_ideas"].insert(row, alter=True)
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
