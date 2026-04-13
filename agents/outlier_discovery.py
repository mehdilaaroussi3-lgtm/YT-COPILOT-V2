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

    def discover_channels(self, keyword: str, max_channels: int = 25) -> list[dict[str, Any]]:
        """YouTube search for channels matching a keyword."""
        params = {
            "part": "snippet",
            "q": keyword,
            "type": "channel",
            "maxResults": min(max_channels, 50),
            "key": self.scraper.api_key,
        }
        import httpx
        resp = httpx.get(f"{API_BASE}/search", params=params, timeout=20.0)
        resp.raise_for_status()
        items = resp.json().get("items", [])
        channels = []
        for it in items:
            sn = it.get("snippet", {})
            cid = sn.get("channelId") or it.get("id", {}).get("channelId")
            if cid:
                channels.append({
                    "channel_id": cid,
                    "name": sn.get("channelTitle") or sn.get("title", ""),
                    "description": sn.get("description", ""),
                })
        return channels

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
        self.db["channels"].upsert({
            "channel_id": channel_id,
            "name": channel_name,
            "median_views": median,
            "last_scanned": dt.datetime.now(dt.UTC).isoformat(),
        }, pk="channel_id", alter=True)

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
