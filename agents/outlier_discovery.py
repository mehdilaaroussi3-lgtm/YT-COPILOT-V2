"""Outlier Discovery Agent (masterplan §25.2).

Given a niche keyword:
1. Search YouTube for top channels in that space
2. For each channel, scan last 50 videos
3. Calculate channel median, score every video, keep 5x+ outliers
4. Download outlier thumbnails to cache
5. Persist to SQLite
"""
from __future__ import annotations

import datetime as dt
from typing import Any

from data.db import db
from scraper.outlier_scorer import get_outliers
from scraper.thumbnail_downloader import download_thumbnail
from scraper.youtube_scraper import API_BASE, ReferenceScraper


class OutlierDiscoveryAgent:
    def __init__(self) -> None:
        self.scraper = ReferenceScraper.from_config()
        self.db = db()

    def discover_channels(self, keyword: str, max_channels: int = 25,
                          min_subscribers: int = 100_000) -> list[dict[str, Any]]:
        """YouTube search for channels matching a keyword.

        Filters by subscriber count so we only learn from established channels
        with real audiences. Long-form content only — Shorts are excluded at
        the scoring stage via is_short().
        """
        import httpx
        params = {
            "part": "snippet",
            "q": keyword,
            "type": "channel",
            "maxResults": min(max_channels, 50),
            "key": self.scraper.api_key,
        }
        resp = httpx.get(f"{API_BASE}/search", params=params, timeout=20.0)
        resp.raise_for_status()
        items = resp.json().get("items", [])
        candidates = []
        for it in items:
            sn = it.get("snippet", {})
            cid = sn.get("channelId") or it.get("id", {}).get("channelId")
            if cid:
                candidates.append({
                    "channel_id": cid,
                    "name": sn.get("channelTitle") or sn.get("title", ""),
                    "description": sn.get("description", ""),
                })

        if not candidates or min_subscribers <= 0:
            return candidates

        # Filter by subscriber count
        try:
            stats = self.scraper.get_channel_stats([c["channel_id"] for c in candidates])
            return [
                c for c in candidates
                if stats.get(c["channel_id"], {}).get("subscriber_count", 0) >= min_subscribers
            ]
        except Exception:  # noqa: BLE001
            return candidates

    def scan_channel(self, channel_id: str, channel_name: str,
                     min_score: float = 5.0,
                     download: bool = True) -> list[dict[str, Any]]:
        """Run full outlier scan on one channel."""
        try:
            outliers = get_outliers(self.scraper, channel_id, min_score=min_score)
        except Exception as e:  # noqa: BLE001
            print(f"  [warn] {channel_name}: {e}")
            return []

        median = outliers[0]["channel_median"] if outliers else 0

        # Enrich with avatar, subs, handle from YouTube API (1 quota unit, batched)
        try:
            ch_info = self.scraper.get_channel_stats([channel_id]).get(channel_id, {})
        except Exception:  # noqa: BLE001
            ch_info = {}

        row: dict = {
            "channel_id": channel_id,
            "name": ch_info.get("title") or channel_name,
            "median_views": median,
            "last_scanned": dt.datetime.now(dt.UTC).isoformat(),
        }
        if ch_info.get("avatar_url"):
            row["avatar_url"] = ch_info["avatar_url"]
        if ch_info.get("subscriber_count"):
            row["subs"] = ch_info["subscriber_count"]
        if ch_info.get("handle"):
            row["handle"] = ch_info["handle"]
        if ch_info.get("description"):
            row["description"] = ch_info["description"]

        self.db["channels"].upsert(row, pk="channel_id", alter=True)

        for v in outliers:
            vid = v["id"]
            sn = v.get("snippet", {})
            self.db["videos"].upsert({
                "video_id": vid,
                "channel_id": channel_id,
                "title": sn.get("title", ""),
                "views": int(v["statistics"].get("viewCount", 0)),
                "outlier_score": v["outlier_score"],
                "published_at": sn.get("publishedAt", ""),
                "fetched_at": dt.datetime.now(dt.UTC).isoformat(),
            }, pk="video_id", alter=True)

            if download:
                p = download_thumbnail(vid)
                if p:
                    self.db["thumbnails"].upsert({
                        "video_id": vid,
                        "file_path": str(p),
                    }, pk="video_id", alter=True)

        return outliers

    def discover_niche(self, keyword: str, max_channels: int = 15,
                        min_score: float = 5.0) -> dict[str, Any]:
        """Full pipeline: keyword → channels → outliers per channel."""
        channels = self.discover_channels(keyword, max_channels=max_channels)
        all_outliers: list[dict[str, Any]] = []
        for ch in channels:
            outs = self.scan_channel(ch["channel_id"], ch["name"], min_score=min_score)
            all_outliers.extend(outs)
        all_outliers.sort(key=lambda v: v["outlier_score"], reverse=True)
        return {
            "keyword": keyword,
            "channels_scanned": len(channels),
            "outliers_found": len(all_outliers),
            "top_outliers": all_outliers[:30],
        }
