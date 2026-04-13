"""Niche Explorer Agent (masterplan §25.5).

Map the competitive landscape for a topic: discover all active channels,
rank by sub count + outlier rate, identify under-served sub-niches.
"""
from __future__ import annotations

from typing import Any

import httpx

from scraper.youtube_scraper import API_BASE, ReferenceScraper


class NicheExplorerAgent:
    def __init__(self) -> None:
        self.scraper = ReferenceScraper.from_config()

    def search_channels(self, keyword: str, max_results: int = 25) -> list[dict[str, Any]]:
        params = {
            "part": "snippet", "q": keyword, "type": "channel",
            "maxResults": min(max_results, 50),
            "key": self.scraper.api_key,
        }
        resp = httpx.get(f"{API_BASE}/search", params=params, timeout=20.0)
        resp.raise_for_status()
        return resp.json().get("items", [])

    def enrich(self, channel_ids: list[str]) -> list[dict[str, Any]]:
        if not channel_ids:
            return []
        params = {
            "part": "snippet,statistics",
            "id": ",".join(channel_ids[:50]),
            "key": self.scraper.api_key,
        }
        resp = httpx.get(f"{API_BASE}/channels", params=params, timeout=20.0)
        resp.raise_for_status()
        return resp.json().get("items", [])

    def explore(self, keyword: str, max_channels: int = 25) -> list[dict[str, Any]]:
        """Search + enrich + sort by subscriber count."""
        results = self.search_channels(keyword, max_results=max_channels)
        ids = [r["snippet"]["channelId"] for r in results
               if r.get("snippet", {}).get("channelId")]
        enriched = self.enrich(ids)
        out = []
        for ch in enriched:
            stats = ch.get("statistics", {})
            sn = ch.get("snippet", {})
            out.append({
                "channel_id": ch["id"],
                "name": sn.get("title", ""),
                "description": sn.get("description", "")[:200],
                "subs": int(stats.get("subscriberCount", 0)),
                "videos": int(stats.get("videoCount", 0)),
                "views": int(stats.get("viewCount", 0)),
            })
        out.sort(key=lambda c: c["subs"], reverse=True)
        return out
