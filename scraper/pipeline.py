"""High-level scrape pipeline: niche → top channels → outliers → thumbnails → style brief."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scraper.cache_manager import (
    ANALYSIS_DIR,
    META_DIR,
    TTL_ANALYSIS,
    TTL_METADATA,
    get_cached,
    set_cached,
)
from scraper.outlier_scorer import get_outliers
from scraper.registry_manager import get_niche
from scraper.thumbnail_downloader import download_thumbnail
from scraper.youtube_scraper import ReferenceScraper


def scrape_niche(
    niche: str,
    per_channel: int = 10,
    min_outlier_score: float = 5.0,
    refresh: bool = False,
) -> dict[str, Any]:
    """Full pipeline for a niche. Returns aggregated outlier list with thumbnail paths."""
    cfg_niche = get_niche(niche)
    channels = cfg_niche["channels"]
    scraper = ReferenceScraper.from_config()

    aggregated: list[dict[str, Any]] = []
    per_channel_summary: list[dict[str, Any]] = []

    for ch in channels:
        ch_name = ch["name"]
        ch_id = ch["channel_id"]

        cache_path = META_DIR / f"channel_{ch_id}_outliers.json"
        cached = None if refresh else get_cached(cache_path, TTL_METADATA)

        if cached is not None:
            outliers = cached["outliers"]
        else:
            try:
                outliers = get_outliers(scraper, ch_id, min_score=min_outlier_score)
                outliers = outliers[:per_channel]
                set_cached(cache_path, {"outliers": outliers, "channel": ch_name})
            except Exception as e:  # noqa: BLE001
                print(f"  [warn] {ch_name} ({ch_id}): {e}")
                per_channel_summary.append({"channel": ch_name, "error": str(e)[:120]})
                continue

        # Download thumbnails for each outlier
        for v in outliers:
            video_id = v.get("id") or v.get("video_id")
            if not video_id:
                continue
            thumb_path = download_thumbnail(video_id)
            v["video_id"] = video_id
            v["thumbnail_path"] = str(thumb_path) if thumb_path else None
            v["channel_name"] = ch_name
            v["style_tags"] = ch.get("style_tags", [])
            aggregated.append(v)

        per_channel_summary.append({
            "channel": ch_name,
            "outlier_count": len(outliers),
        })

    aggregated.sort(key=lambda v: v.get("outlier_score", 0), reverse=True)

    return {
        "niche": niche,
        "channels_scanned": len(channels),
        "outliers": aggregated,
        "summary": per_channel_summary,
    }


def get_or_build_style_brief(niche: str, refresh: bool = False) -> str:
    """Get cached style brief for a niche, or build it from cached thumbnails."""
    from scraper.thumbnail_analyzer import analyze_thumbnails

    cache_path = ANALYSIS_DIR / f"{niche}_brief.json"
    cached = None if refresh else get_cached(cache_path, TTL_ANALYSIS)
    if cached is not None:
        return cached["brief"]

    # Need cached thumbnails — scrape if necessary
    result = scrape_niche(niche, refresh=False)
    thumb_paths = [Path(o["thumbnail_path"]) for o in result["outliers"]
                   if o.get("thumbnail_path")][:8]

    brief = analyze_thumbnails(thumb_paths, niche)
    set_cached(cache_path, {"brief": brief, "thumb_count": len(thumb_paths)})
    return brief
