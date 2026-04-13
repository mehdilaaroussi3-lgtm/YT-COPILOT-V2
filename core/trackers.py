"""Personal tracked-channels CRUD.

Coexists with scraper/channels_registry.yml — that's the curated seed list,
this module manages user-added channels persisted in SQLite. NO UPLOAD LIMIT.
"""
from __future__ import annotations

import datetime as dt
import re
from typing import Any

import httpx

from data.db import db
from scraper.youtube_scraper import API_BASE, ReferenceScraper


HANDLE_RE = re.compile(r"@?([A-Za-z0-9_.-]+)")


def _enrich_by_id(channel_id: str,
                   fallback_name: str = "",
                   fallback_handle: str = "") -> tuple[str, str, str, int, str, str]:
    """(channel_id, handle, name, subs, description, avatar_url)"""
    scraper = ReferenceScraper.from_config()
    resp = httpx.get(f"{API_BASE}/channels", params={
        "part": "snippet,statistics", "id": channel_id,
        "key": scraper.api_key,
    }, timeout=20.0)
    if resp.status_code == 200 and resp.json().get("items"):
        item = resp.json()["items"][0]
        sn = item.get("snippet", {})
        stats = item.get("statistics", {})
        thumbs = sn.get("thumbnails", {})
        avatar = (thumbs.get("medium") or thumbs.get("default") or {}).get("url", "")
        custom_url = sn.get("customUrl") or fallback_handle or ""
        return (
            channel_id,
            custom_url.lstrip("@"),
            sn.get("title", fallback_name),
            int(stats.get("subscriberCount", 0)),
            sn.get("description", "") or "",
            avatar,
        )
    return channel_id, fallback_handle, fallback_name, 0, "", ""


def _resolve_handle(handle_or_url: str) -> tuple[str, str, str, int, str, str] | None:
    raw = handle_or_url.strip()

    # Direct channel URL with /channel/UC...
    if "youtube.com" in raw:
        m = re.search(r"channel/([A-Za-z0-9_-]+)", raw)
        if m:
            return _enrich_by_id(m.group(1))
        m = re.search(r"@([A-Za-z0-9_.-]+)", raw)
        if not m:
            return None
        handle = m.group(1)
    else:
        m = HANDLE_RE.match(raw)
        if not m:
            return None
        handle = m.group(1)

    scraper = ReferenceScraper.from_config()
    resp = httpx.get(f"{API_BASE}/search", params={
        "part": "snippet", "q": f"@{handle}",
        "type": "channel", "maxResults": 5,
        "key": scraper.api_key,
    }, timeout=20.0)
    resp.raise_for_status()
    items = resp.json().get("items", [])
    for it in items:
        sn = it.get("snippet", {})
        name = (sn.get("channelTitle") or sn.get("title", "")).strip()
        cid = sn.get("channelId") or it.get("id", {}).get("channelId")
        if not cid:
            continue
        return _enrich_by_id(cid, fallback_name=name, fallback_handle=handle)
    return None


# ---- Public API -------------------------------------------------------------

def list_tracked() -> list[dict[str, Any]]:
    d = db()
    rows = list(d["tracked_channels"].rows_where(order_by="is_default desc, added_at asc"))
    return rows


def add_tracked(handle_or_url: str, niche_override: str = "") -> dict[str, Any]:
    resolved = _resolve_handle(handle_or_url)
    if resolved is None:
        raise ValueError(f"Could not resolve YouTube channel from: {handle_or_url}")
    channel_id, handle, name, subs, description, avatar = resolved
    now = dt.datetime.now(dt.UTC).isoformat()
    d = db()

    # First channel → make it default automatically
    is_default = 0 if d["tracked_channels"].count > 0 else 1

    row = {
        "channel_id": channel_id,
        "handle": handle,
        "name": name,
        "subs": subs,
        "description": description,
        "ai_summary": "",
        "avatar_url": avatar,
        "is_default": is_default,
        "added_at": now,
        "last_scanned": "",
        "niche_override": niche_override,
    }
    d["tracked_channels"].upsert(row, pk="channel_id", alter=True)

    # Synthesize the smart description. Best-effort — if Gemini fails the add
    # still succeeds and the UI falls back to the raw description.
    try:
        from core.channel_summary import synthesize
        summary = synthesize(channel_id)
        if summary:
            row["ai_summary"] = summary
    except Exception:  # noqa: BLE001
        pass

    return row


def remove_tracked(channel_id: str) -> None:
    d = db()
    d["tracked_channels"].delete(channel_id)
    # If we deleted the default, promote first remaining
    remaining = list(d["tracked_channels"].rows_where(order_by="added_at asc"))
    if remaining and not any(r.get("is_default") for r in remaining):
        d["tracked_channels"].update(remaining[0]["channel_id"], {"is_default": 1})


def set_default(channel_id: str) -> None:
    d = db()
    for row in d["tracked_channels"].rows_where():
        d["tracked_channels"].update(row["channel_id"], {"is_default": 1 if row["channel_id"] == channel_id else 0})


def mark_scanned(channel_id: str) -> None:
    d = db()
    d["tracked_channels"].update(channel_id, {
        "last_scanned": dt.datetime.now(dt.UTC).isoformat(),
    })
