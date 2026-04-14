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


TITLE_CHANNEL_DNA_PROMPT = """\
You are writing YouTube title variants in the EXACT voice of a specific
channel, for a new video.

CHANNEL: {channel} ({niche})
VIDEO IDEA / WORKING TITLE:
"{idea}"

The following are {sample_count} REAL titles from this channel's past videos.
Study their pattern — the sentence rhythm, vocabulary register, punctuation,
the way they open hooks — and write NEW titles that would feel at home in
this list.

CHANNEL'S REAL TITLES:
{channel_titles}

Generate {count} DISTINCT title variants INSPIRED BY THE CHANNEL'S VOICE.
- Mimic the channel's signature phrasing, sentence length, punctuation,
  capitalisation quirks. If the channel writes in lowercase, you do too.
- Each variant uses a different emotional angle (curiosity / threat / anger
  / authority / mystery / contrarian / confession / reveal / warning / flex).
- Stay tight: 5-7 words when possible.
- Language matches the VIDEO IDEA's language, not the channel's (if they
  differ).

Output STRICT JSON: an array of {count} objects `{{"title": "...", "angle": "..."}}`.
No prose, no fence.
"""


TITLE_OUTLIER_PROMPT = """\
You are writing YouTube title variants inspired by proven VIRAL OUTLIER
titles from high-performing videos, for a new video.

CHANNEL: {channel} ({niche})
VIDEO IDEA / WORKING TITLE:
"{idea}"

Below are real titles from top-performing outlier videos — the click-magnets,
the ones that massively over-perform. Study what makes them work (the hook
shape, the stakes, the curiosity gap) and write NEW titles that borrow their
FORMULA, applied to the video idea above.

REAL OUTLIER TITLES:
{outlier_titles}

Generate {count} DISTINCT title variants INSPIRED BY OUTLIER FORMULAS.
- Borrow the STRUCTURAL patterns of the outliers (e.g. "I [verb] the [noun]
  that [consequence]", "The [noun] they don't want you to see", etc).
- Each variant uses a different formula from the examples. Do not reuse the
  outlier's exact topic — adapt the structure to the video idea.
- Language matches the VIDEO IDEA's language.

Output STRICT JSON: an array of {count} objects `{{"title": "...", "angle": "..."}}`.
No prose, no fence.
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


def generate_titles_dual(channel: str, idea: str,
                           per_source: int = 10) -> dict[str, list[dict]]:
    """Generate two parallel title groups:
      - `channel_titles`: inspired by the channel's own past video titles
      - `outlier_titles`: inspired by top outlier titles (viral formulas)

    Returns {"channel_titles": [...], "outlier_titles": [...]}.
    Each title is a dict `{title, angle, char_count, source}` already
    persisted to the DB with a shared `batch_id` tying the two groups
    together.
    """
    profile = load_profile(channel)
    niche = profile.get("niche", "documentary_essay")
    display_name = profile.get("name", channel)

    # Pull channel's real titles (up to 15) and top outlier titles (up to 15)
    channel_titles_sample = _sample_channel_titles(channel, limit=15)
    outlier_titles_sample = _sample_outlier_titles(channel, niche, limit=15)

    # Run both prompts in sequence (cheap — two text calls)
    channel_items: list[dict] = []
    outlier_items: list[dict] = []

    if channel_titles_sample:
        try:
            raw = generate_text(
                TITLE_CHANNEL_DNA_PROMPT.format(
                    channel=display_name, niche=niche, idea=idea.strip(),
                    count=per_source,
                    sample_count=len(channel_titles_sample),
                    channel_titles="\n".join(f"- {t}" for t in channel_titles_sample),
                ),
                temperature=0.85,
            )
            channel_items = _parse_json_array(raw)
        except Exception:  # noqa: BLE001
            channel_items = []

    if not channel_items:
        # Fallback: use the generic prompt so the column isn't empty
        try:
            raw = generate_text(
                TITLE_PROMPT.format(
                    channel=display_name, niche=niche, idea=idea.strip(),
                    count=per_source,
                ),
                temperature=0.8,
            )
            channel_items = _parse_json_array(raw)
        except Exception:  # noqa: BLE001
            channel_items = []

    if outlier_titles_sample:
        try:
            raw = generate_text(
                TITLE_OUTLIER_PROMPT.format(
                    channel=display_name, niche=niche, idea=idea.strip(),
                    count=per_source,
                    outlier_titles="\n".join(f"- {t}" for t in outlier_titles_sample),
                ),
                temperature=0.95,
            )
            outlier_items = _parse_json_array(raw)
        except Exception:  # noqa: BLE001
            outlier_items = []

    # Persist everything with a shared batch_id so history groups them
    batch_id = uuid.uuid4().hex[:12]
    now = dt.datetime.now(dt.UTC).isoformat()
    d = db()

    def _persist(items: list[dict], source: str) -> list[dict]:
        out: list[dict] = []
        for item in items[:per_source]:
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
                "source": source,
            }
            d["generated_titles"].insert(row, alter=True)
            out.append({
                **row,
                "angle": (item.get("angle") or "").strip(),
                "id": d["generated_titles"].last_pk,
            })
        return out

    return {
        "channel_titles": _persist(channel_items, "channel"),
        "outlier_titles": _persist(outlier_items, "outlier"),
    }


def _sample_channel_titles(channel: str, limit: int = 15) -> list[str]:
    """Return up to `limit` titles from the channel's scraped videos."""
    if not channel or not channel.startswith("UC"):
        return []
    try:
        d = db()
        rows = list(d["videos"].rows_where(
            "channel_id = ?", [channel],
            order_by="outlier_score desc", limit=limit,
        ))
        return [r.get("title", "").strip() for r in rows if r.get("title", "").strip()]
    except Exception:  # noqa: BLE001
        return []


def _sample_outlier_titles(channel: str, niche: str, limit: int = 15) -> list[str]:
    """Return up to `limit` high-scoring outlier titles from OTHER channels.

    Used as 'viral formula' examples. Excludes the current channel so we
    don't double-count with the channel-DNA prompt.
    """
    try:
        d = db()
        rows = list(d["videos"].rows_where(
            "outlier_score >= 2.0 AND channel_id != ?", [channel or ""],
            order_by="outlier_score desc", limit=limit * 2,
        ))
        titles = [r.get("title", "").strip() for r in rows if r.get("title", "").strip()]
        return titles[:limit]
    except Exception:  # noqa: BLE001
        return []


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
