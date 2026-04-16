"""Outlier scoring (the 1of10 core mechanism, masterplan §24.3).

Outlier Score = Video Views / Channel Median Views.
Only learn from 5x+ outliers — these are the videos where PACKAGING
(title + thumbnail) drove the over-performance, not just channel size.
"""
from __future__ import annotations

import re
import statistics
from typing import Any

from scraper.youtube_scraper import ReferenceScraper


def _parse_duration_s(iso: str) -> float:
    """Parse ISO 8601 duration (PT4M13S, PT59S, PT1H2M3S) → total seconds."""
    if not iso:
        return 0.0
    m = re.match(
        r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?",
        iso,
    )
    if not m:
        return 0.0
    h, mn, s = (int(x or 0) for x in m.groups())
    return h * 3600 + mn * 60 + s


def is_short(video: dict[str, Any]) -> bool:
    """Return True if this video is a YouTube Short (≤ 65 seconds).

    Shorts are excluded from Smart Find — the app is long-format only.
    We also skip videos with #Shorts in the title as an extra safety net.
    """
    duration_s = _parse_duration_s(
        (video.get("contentDetails") or {}).get("duration", "")
    )
    if 0 < duration_s <= 65:
        return True
    title = (video.get("snippet") or {}).get("title", "").lower()
    return "#shorts" in title or "#short" in title


def channel_median(scraper: ReferenceScraper, channel_id: str,
                    sample: int = 50) -> tuple[float, list[dict[str, Any]]]:
    """Return (median_views, all_videos_with_stats) for a channel."""
    ids = scraper.get_recent_video_ids(channel_id, max_results=sample)
    videos = scraper.get_videos_with_stats(ids)
    if not videos:
        return 0.0, []
    views = [int(v["statistics"].get("viewCount", 0)) for v in videos]
    return float(statistics.median(views)), videos


def score_video(video: dict[str, Any], median: float) -> float:
    if median <= 0:
        return 0.0
    views = int(video["statistics"].get("viewCount", 0))
    return round(views / median, 2)


def is_likely_ad(video: dict[str, Any]) -> bool:
    """Return True if this video looks like a paid ad (inflated views, near-zero engagement).

    Ads are served millions of times but almost nobody likes or comments on them,
    producing a tell-tale engagement signature: like_rate < 0.05% and comment_rate < 0.005%.
    We only apply this check above 500k views to avoid penalising small legitimate videos.
    """
    stats = video.get("statistics", {})
    views = int(stats.get("viewCount", 0))
    if views < 500_000:
        return False
    likes = int(stats.get("likeCount") or 0)
    comments = int(stats.get("commentCount") or 0)
    like_rate = likes / views
    comment_rate = comments / views
    return like_rate < 0.0005 and comment_rate < 0.00005


def get_outliers(scraper: ReferenceScraper, channel_id: str,
                  min_score: float = 5.0,
                  sample: int = 50) -> list[dict[str, Any]]:
    """Return only videos with outlier_score >= min_score, sorted descending.

    Ads with artificially inflated view counts are excluded via engagement-rate check.
    """
    median, videos = channel_median(scraper, channel_id, sample=sample)
    outliers: list[dict[str, Any]] = []
    for v in videos:
        if is_short(v):          # skip Shorts — long-format only
            continue
        if is_likely_ad(v):
            continue
        score = score_video(v, median)
        if score >= min_score:
            outliers.append({
                **v,
                "outlier_score": score,
                "channel_median": median,
            })
    outliers.sort(key=lambda v: v["outlier_score"], reverse=True)
    return outliers
