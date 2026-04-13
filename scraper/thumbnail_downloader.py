"""Download thumbnails from YouTube CDN with quality fallback chain."""
from __future__ import annotations

from pathlib import Path

import httpx

from scraper.cache_manager import THUMB_DIR

QUALITY_CHAIN = ["maxresdefault", "sddefault", "hqdefault", "mqdefault", "default"]


def download_thumbnail(video_id: str, force: bool = False) -> Path | None:
    """Download highest available thumbnail for a video. Cached forever."""
    for quality in QUALITY_CHAIN:
        path = THUMB_DIR / f"{video_id}_{quality}.jpg"
        if path.exists() and not force and path.stat().st_size > 1000:
            return path
        url = f"https://img.youtube.com/vi/{video_id}/{quality}.jpg"
        try:
            resp = httpx.get(url, timeout=15.0)
        except httpx.HTTPError:
            continue
        # YouTube returns a 120x90 grey "no image" placeholder (~1KB) when a
        # quality tier doesn't exist. Skip those.
        if resp.status_code == 200 and len(resp.content) > 1000:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(resp.content)
            return path
    return None


def best_cached(video_id: str) -> Path | None:
    for quality in QUALITY_CHAIN:
        path = THUMB_DIR / f"{video_id}_{quality}.jpg"
        if path.exists() and path.stat().st_size > 1000:
            return path
    return None
