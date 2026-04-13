"""YouTube Data API v3 client.

Pulls channel metadata, recent videos, and stats. Batched to keep quota usage low
(~11 units per niche scan per masterplan §3.8).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from cli import config as cfg

API_BASE = "https://www.googleapis.com/youtube/v3"


class YouTubeAPIError(RuntimeError):
    pass


@dataclass
class ReferenceScraper:
    api_key: str

    @classmethod
    def from_config(cls) -> "ReferenceScraper":
        key = cfg.get("youtube.api_key")
        if not key or key.startswith("your-"):
            raise YouTubeAPIError(
                "youtube.api_key is not set in config.yml. "
                "Create one at console.cloud.google.com (it should start with 'AIza')."
            )
        return cls(api_key=key)

    def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        params = {**params, "key": self.api_key}
        resp = httpx.get(f"{API_BASE}/{path}", params=params, timeout=20.0)
        if resp.status_code != 200:
            raise YouTubeAPIError(
                f"YouTube API {path} failed: HTTP {resp.status_code} — {resp.text[:300]}"
            )
        return resp.json()

    # --- High-level helpers -------------------------------------------------
    def get_uploads_playlist(self, channel_id: str) -> str:
        data = self._get("channels", {"part": "contentDetails", "id": channel_id})
        items = data.get("items") or []
        if not items:
            raise YouTubeAPIError(f"Channel not found: {channel_id}")
        return items[0]["contentDetails"]["relatedPlaylists"]["uploads"]

    def get_recent_video_ids(self, channel_id: str, max_results: int = 50) -> list[str]:
        playlist_id = self.get_uploads_playlist(channel_id)
        data = self._get("playlistItems", {
            "part": "snippet",
            "playlistId": playlist_id,
            "maxResults": min(max_results, 50),
        })
        return [item["snippet"]["resourceId"]["videoId"] for item in data.get("items", [])]

    def get_videos_with_stats(self, video_ids: list[str]) -> list[dict[str, Any]]:
        if not video_ids:
            return []
        # videos.list supports up to 50 ids per call (1 quota unit)
        all_videos: list[dict[str, Any]] = []
        for i in range(0, len(video_ids), 50):
            batch = video_ids[i:i + 50]
            data = self._get("videos", {
                "part": "statistics,snippet",
                "id": ",".join(batch),
            })
            all_videos.extend(data.get("items", []))
        return all_videos

    def get_top_videos(self, channel_id: str, max_results: int = 10) -> list[dict[str, Any]]:
        """Pull recent videos, sort by view count, return top N."""
        ids = self.get_recent_video_ids(channel_id, max_results=50)
        videos = self.get_videos_with_stats(ids)
        videos.sort(key=lambda v: int(v["statistics"].get("viewCount", 0)), reverse=True)
        return videos[:max_results]
