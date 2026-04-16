"""Resolve a 'style from channel' selection into reference thumbnails + style brief.

Used by the Thumbnail Generator when the user picks a specific channel whose
artistic style they want the new thumbnail to emulate. Works with tracked
channels AND on-the-fly @handle lookups — if the channel hasn't been scanned
yet, this runs a scan first.
"""
from __future__ import annotations

import base64
import datetime as dt
from pathlib import Path
from typing import Any

import httpx

from cli import config as cfg
from generators import gcp_auth
from data.db import db
from scraper.outlier_scorer import channel_median, get_outliers, score_video
from scraper.thumbnail_downloader import download_thumbnail
from scraper.youtube_scraper import API_BASE, ReferenceScraper

VERTEX_HOST = "https://aiplatform.googleapis.com"
ENDPOINT_TMPL = "/v1/publishers/google/models/{model}:generateContent"

CHANNEL_BRIEF_PROMPT = """\
You are a YouTube thumbnail style analyst.

I'm showing you {count} thumbnails from a single creator's TOP PERFORMING
videos. These are their outliers — the ones that massively over-performed
their own channel average.

Extract ONLY the visual DNA that recurs across these thumbnails:

1. COLOR PALETTE: 3-5 exact dominant hex codes. Background palette vs
   accent palette. Warm vs cool tendency.
2. COMPOSITION: Where does the focal subject live? Frame fill %. Any
   recurring framing (tight crop, full-scene, split-panel, etc.)?
3. LIGHTING: Rim? Hard directional? Soft ambient? Warm vs cool?
4. TEXT TREATMENT: Present or absent? If present: placement, font
   character (tall/condensed/rounded), color, stroke/shadow.
5. VISUAL ARTEFACTS: Recurring props, icons, decals, borders, grain,
   vignette, treatment (noir, cyberpunk, editorial, etc).
6. EMOTIONAL TONE: What feeling dominates?
7. SIGNATURE ELEMENT: The one thing that makes these INSTANTLY
   recognisable as this creator's work.

Output a tight, concrete STYLE BRIEF (300-400 words) written as directives
for a generative image model. Be specific — name the colors, the angles,
the moods. No generic language.
"""


def resolve_style_channel(channel_id: str, handle_or_url: str | None = None,
                            force_rescan: bool = False) -> dict[str, Any] | None:
    """Ensure we have outliers + thumbnails + a style brief for this channel.

    Returns {
      'channel_id', 'name', 'handle',
      'reference_paths': [Path, ...],   # up to 2 best outlier thumbs
      'style_brief': str,
      'scanned_this_call': bool,
    }
    """
    d = db()
    meta = None
    looks_like_id = isinstance(channel_id, str) and channel_id.startswith("UC") and len(channel_id) >= 20

    def _safe_get(table: str, pk: str):
        try:
            return d[table].get(pk)
        except Exception:  # noqa: BLE001
            return None

    if looks_like_id:
        meta = _safe_get("tracked_channels", channel_id) or _safe_get("channels", channel_id)

    # If not cached OR the input isn't a channel ID (e.g. @handle / URL), resolve it.
    if meta is None:
        lookup = handle_or_url or (None if looks_like_id else channel_id)
        if lookup:
            try:
                from core.trackers import add_tracked
                row = add_tracked(lookup)
                channel_id = row["channel_id"]
                meta = row
            except Exception as _e:  # noqa: BLE001
                import sys
                print(f"[style_channel] resolve failed for {lookup!r}: {_e}", file=sys.stderr)
                return None

    if meta is None:
        return None

    scrape_count: int = max(1, int(cfg.get("channel.scrape_count", 10)))

    existing = list(d["videos"].rows_where(
        "channel_id = ?",
        [channel_id], order_by="outlier_score desc", limit=scrape_count,
    ))

    scanned = False
    if len(existing) < scrape_count or force_rescan:
        # Pull the channel's recent videos and cache their thumbnails.
        # scrape_count is the single source of truth — set in config.yml.
        scraper = ReferenceScraper.from_config()
        median, videos = channel_median(scraper, channel_id, sample=scrape_count)
        for v in videos:
            vid = v["id"]
            sn = v.get("snippet", {})
            try:
                score = score_video(v, median)
            except Exception:  # noqa: BLE001
                score = 0.0
            d["videos"].upsert({
                "video_id": vid,
                "channel_id": channel_id,
                "title": sn.get("title", ""),
                "views": int(v.get("statistics", {}).get("viewCount", 0)),
                "outlier_score": score,
                "published_at": sn.get("publishedAt", ""),
                "fetched_at": dt.datetime.now(dt.UTC).isoformat(),
            }, pk="video_id", alter=True)
            p = download_thumbnail(vid)
            if p:
                d["thumbnails"].upsert({
                    "video_id": vid, "file_path": str(p),
                }, pk="video_id", alter=True)
        scanned = True
        existing = list(d["videos"].rows_where(
            "channel_id = ?",
            [channel_id], order_by="outlier_score desc", limit=scrape_count,
        ))

    # Collect cached thumbnail paths
    thumb_paths: list[Path] = []
    for row in existing:
        vid = row["video_id"]
        th = _safe_get("thumbnails", vid)
        if th and th.get("file_path") and Path(th["file_path"]).exists():
            thumb_paths.append(Path(th["file_path"]))

    # Build or reuse style brief
    brief = _build_channel_brief(channel_id, thumb_paths, scrape_count)

    # Build or reuse text DNA (channel's typographic voice)
    text_dna = ""
    try:
        from core.channel_text_dna import build_text_dna
        text_dna = build_text_dna(channel_id, thumb_paths[:scrape_count])
    except Exception:  # noqa: BLE001
        text_dna = ""

    return {
        "channel_id": channel_id,
        "name": meta.get("name", ""),
        "handle": meta.get("handle", ""),
        "reference_paths": thumb_paths[:2],        # Gemini image-gen API hard limit
        "all_reference_paths": thumb_paths,        # pipeline spreads across variants
        "style_brief": brief,
        "text_dna": text_dna,
        "scanned_this_call": scanned,
    }


def _build_channel_brief(channel_id: str, thumb_paths: list[Path],
                          scrape_count: int = 10) -> str:
    """Cache per-channel style briefs in the channels table."""
    d = db()
    # Use a dedicated key in the thumbnails table — we don't want to touch the
    # schema. Store the brief as a thumbnails row keyed by channel_id with a
    # special prefix. Simpler: reuse the research table (no — keep it clean).
    # Best: a tiny dedicated table.
    if "channel_briefs" not in d.table_names():
        d["channel_briefs"].create({
            "channel_id": str,
            "brief": str,
            "thumb_count": int,
            "built_at": str,
        }, pk="channel_id")

    try:
        existing = d["channel_briefs"].get(channel_id)
    except Exception:  # noqa: BLE001
        existing = None
    if existing and existing.get("thumb_count") == len(thumb_paths):
        return existing["brief"]

    if not thumb_paths:
        return ""

    # Gemini Vision
    try:
        model = cfg.get("gemini.vision_model", "gemini-2.5-pro")
        url = gcp_auth.vertex_url(model)
    except Exception:  # noqa: BLE001
        return ""

    parts: list[dict] = []
    for p in thumb_paths[:scrape_count]:
        parts.append({"inlineData": {
            "data": base64.b64encode(p.read_bytes()).decode(),
            "mimeType": "image/jpeg",
        }})
    parts.append({"text": CHANNEL_BRIEF_PROMPT.format(count=len(thumb_paths[:scrape_count]))})

    try:
        with httpx.Client(timeout=120.0) as c:
            resp = c.post(url, json={
                "contents": [{"role": "user", "parts": parts}],
                "generationConfig": {"responseModalities": ["TEXT"]},
            }, headers=gcp_auth.auth_headers())
        if resp.status_code >= 300:
            return ""
        payload = resp.json()
        texts = []
        for cand in payload.get("candidates", []):
            for part in (cand.get("content") or {}).get("parts", []):
                if "text" in part:
                    texts.append(part["text"])
        brief = "\n".join(texts).strip()
    except Exception:  # noqa: BLE001
        return ""

    if brief:
        d["channel_briefs"].upsert({
            "channel_id": channel_id,
            "brief": brief,
            "thumb_count": len(thumb_paths),
            "built_at": dt.datetime.now(dt.UTC).isoformat(),
        }, pk="channel_id", alter=True)
    return brief


def list_style_channels() -> list[dict[str, Any]]:
    """Union of tracked channels + registry-seed channels (if any outliers
    have actually been scanned)."""
    d = db()
    out = []
    for r in d["tracked_channels"].rows_where(order_by="added_at desc"):
        out.append({
            "channel_id": r["channel_id"],
            "name": r["name"] or r["handle"],
            "handle": r["handle"],
            "subs": r.get("subs", 0),
            "source": "tracked",
        })
    for r in d["channels"].rows_where(order_by="name"):
        if r.get("channel_id") and r["channel_id"] not in {x["channel_id"] for x in out}:
            # Only include registry channels with scanned videos
            n = d["videos"].count_where("channel_id = ?", [r["channel_id"]])
            if n > 0:
                out.append({
                    "channel_id": r["channel_id"],
                    "name": r.get("name", ""),
                    "handle": "",
                    "subs": r.get("subs", 0),
                    "source": "registry",
                })
    return out
