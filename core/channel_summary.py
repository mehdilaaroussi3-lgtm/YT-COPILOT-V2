"""AI-synthesized channel summaries.

Instead of showing YouTube's raw self-description (which is often empty, overly
promotional, or just a link dump), we generate a tight editorial-style summary
grounded in:
  - channel name + raw description
  - the creator's latest 25 video titles
  - their subscriber count

Produces a 4-6 sentence paragraph describing what the channel actually covers,
the recurring themes, format, tone, and why viewers show up.
"""
from __future__ import annotations

import datetime as dt

import httpx

from data.db import db
from generators.gemini_text import generate_text
from scraper.youtube_scraper import API_BASE, ReferenceScraper


SUMMARY_PROMPT = """\
You are a senior YouTube strategist writing an editorial profile of a channel.

CHANNEL: {name}
HANDLE: @{handle}
SUBSCRIBERS: {subs}
CREATOR'S OWN DESCRIPTION:
{raw_description}

LATEST {n_titles} VIDEO TITLES (most recent first):
{titles}

Write a tight, investigative 4-6 sentence paragraph describing this channel.
Cover:
- What subject matter, recurring themes, and story types they cover
- The format (long-form documentary, rapid explainer, narrative essay, etc.)
- The editorial voice and tone (investigative, sensational, dry, cinematic, etc.)
- What makes their content distinctive vs. adjacent channels
- Who the audience is and why they return

Do NOT list titles verbatim. Do NOT hype — no "incredible", "mind-blowing", etc.
Do NOT start with "This channel" or "The channel". Do NOT wrap in quotes or
markdown. Output plain prose only, one paragraph, no headings.
"""


def _fetch_recent_titles(channel_id: str, limit: int = 25) -> list[str]:
    """Pull the channel's most recent video titles via YouTube Data API."""
    scraper = ReferenceScraper.from_config()
    try:
        playlist_id = scraper.get_uploads_playlist(channel_id)
    except Exception:  # noqa: BLE001
        return []

    resp = httpx.get(f"{API_BASE}/playlistItems", params={
        "part": "snippet",
        "playlistId": playlist_id,
        "maxResults": min(limit, 50),
        "key": scraper.api_key,
    }, timeout=20.0)
    if resp.status_code != 200:
        return []
    items = resp.json().get("items", [])
    out = []
    for it in items:
        t = (it.get("snippet") or {}).get("title")
        if t:
            out.append(t)
    return out[:limit]


def synthesize(channel_id: str) -> str:
    """Run synthesis, persist result to tracked_channels.ai_summary, return it."""
    d = db()
    if channel_id not in d["tracked_channels"].pks:
        return ""
    row = d["tracked_channels"].get(channel_id)

    titles = _fetch_recent_titles(channel_id, limit=25)
    if not titles and not (row.get("description") or "").strip():
        # Not enough signal — skip rather than write a generic filler.
        return ""

    prompt = SUMMARY_PROMPT.format(
        name=row.get("name") or row.get("handle") or "Unknown",
        handle=row.get("handle") or "",
        subs=f"{(row.get('subs') or 0):,}",
        raw_description=(row.get("description") or "")[:1500] or "(no description provided by creator)",
        titles="\n".join(f"- {t}" for t in titles) or "(no titles available)",
        n_titles=len(titles),
    )

    try:
        summary = generate_text(prompt, temperature=0.55).strip()
    except Exception:  # noqa: BLE001
        return ""

    # Strip common lead-ins Gemini falls into
    for dead in ("This channel", "The channel", '"', "“"):
        if summary.startswith(dead):
            summary = summary.lstrip('"').lstrip("“").lstrip()
            if summary.lower().startswith(("this channel", "the channel")):
                idx = summary.find(" ", summary.find(" ") + 1) + 1
                if idx > 0:
                    summary = summary[idx:].lstrip().capitalize()
            break

    d["tracked_channels"].update(channel_id, {"ai_summary": summary})
    return summary


def regenerate_if_stale(channel_id: str) -> str:
    """Generate only if we don't already have one. Safe to call repeatedly."""
    d = db()
    if channel_id not in d["tracked_channels"].pks:
        return ""
    existing = d["tracked_channels"].get(channel_id).get("ai_summary") or ""
    if existing.strip():
        return existing
    return synthesize(channel_id)
