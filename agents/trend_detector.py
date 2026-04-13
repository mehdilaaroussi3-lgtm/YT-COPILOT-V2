"""Trend Detector Agent (masterplan §25.6).

Compare style-tag frequency in outliers from THIS WEEK vs LAST MONTH.
Flag rising styles (opportunity) and saturating ones (warning).
"""
from __future__ import annotations

import datetime as dt
from collections import Counter

from data.db import db


class TrendDetectorAgent:
    def __init__(self) -> None:
        self.db = db()

    def detect(self, niche: str, recent_days: int = 14,
                baseline_days: int = 60) -> dict:
        now = dt.datetime.now(dt.UTC)
        recent_cutoff = (now - dt.timedelta(days=recent_days)).isoformat()
        baseline_cutoff = (now - dt.timedelta(days=baseline_days)).isoformat()

        # Pull thumbnails published in each window. Join via videos.
        recent_tags = self._collect_tags(recent_cutoff, now.isoformat())
        baseline_tags = self._collect_tags(baseline_cutoff, recent_cutoff)

        all_tags = set(recent_tags) | set(baseline_tags)
        report = []
        for tag in all_tags:
            r = recent_tags.get(tag, 0)
            b = baseline_tags.get(tag, 0)
            # Normalize per period
            r_rate = r / max(recent_days, 1)
            b_rate = b / max(baseline_days, 1)
            direction = "flat"
            if r_rate > b_rate * 1.5 and r >= 2:
                direction = "rising"
            elif r_rate < b_rate * 0.5 and b >= 2:
                direction = "falling"
            report.append({
                "tag": tag, "recent": r, "baseline": b,
                "direction": direction,
            })
        report.sort(key=lambda x: x["recent"], reverse=True)
        return {"niche": niche, "report": report}

    def _collect_tags(self, start: str, end: str) -> dict[str, int]:
        sql = """
        SELECT t.style_tags FROM thumbnails t
        JOIN videos v ON v.video_id = t.video_id
        WHERE v.published_at >= ? AND v.published_at < ?
        """
        counts: Counter = Counter()
        for row in self.db.query(sql, [start, end]):
            for tag in (row.get("style_tags") or "").split(","):
                tag = tag.strip().lower()
                if tag:
                    counts[tag] += 1
        return dict(counts)
