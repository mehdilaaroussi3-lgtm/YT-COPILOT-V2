"""Outlier scoring (the 1of10 core mechanism, masterplan §24.3).

Outlier Score = Video Views / Channel Median Views.
Only learn from 5x+ outliers — these are the videos where PACKAGING
(title + thumbnail) drove the over-performance, not just channel size.
"""
from __future__ import annotations

import statistics
from typing import Any

from scraper.youtube_scraper import ReferenceScraper


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


def get_outliers(scraper: ReferenceScraper, channel_id: str,
                  min_score: float = 5.0,
                  sample: int = 50) -> list[dict[str, Any]]:
    """Return only videos with outlier_score >= min_score, sorted descending."""
    median, videos = channel_median(scraper, channel_id, sample=sample)
    outliers: list[dict[str, Any]] = []
    for v in videos:
        score = score_video(v, median)
        if score >= min_score:
            outliers.append({
                **v,
                "outlier_score": score,
                "channel_median": median,
            })
    outliers.sort(key=lambda v: v["outlier_score"], reverse=True)
    return outliers
