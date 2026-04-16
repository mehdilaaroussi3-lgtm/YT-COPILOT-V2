"""Refresh template example_video_ids with REAL videos from the scraped DB.

Replaces placeholder IDs (Rick Astley, etc.) with real outlier videos whose titles
best match each template's name/description. Picks top-scored matches by keyword
overlap and outlier_score.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone

from data.db import db as get_db


STOPWORDS = {
    "the", "a", "an", "of", "in", "on", "at", "to", "for", "and", "or", "but", "is",
    "are", "was", "were", "be", "been", "being", "have", "has", "had", "do", "does",
    "did", "will", "would", "could", "should", "this", "that", "these", "those",
    "by", "with", "as", "from", "who", "what", "where", "when", "why", "how",
    "n", "x", "job", "industry", "country", "thing", "person", "company", "place",
    "year", "years", "secret", "story", "side",
}


def _tokens(s: str) -> set[str]:
    """Extract searchable keyword tokens from a template name/description."""
    # Strip placeholders like [Job], [X], [Country]
    s = re.sub(r"\[[^\]]*\]", " ", s or "")
    # Lowercase + word-only
    words = re.findall(r"[a-zA-Z]{3,}", s.lower())
    return {w for w in words if w not in STOPWORDS}


def _score_video(keywords: set[str], title: str, outlier_score: float | None) -> float:
    """Score a video: keyword overlap (weighted) + small outlier_score bonus."""
    if not title:
        return 0.0
    tset = _tokens(title)
    overlap = len(keywords & tset)
    if overlap == 0:
        return 0.0
    return overlap * 10.0 + (outlier_score or 0.0)


def refresh_examples(per_template: int = 6) -> None:
    d = get_db()
    if "templates" not in d.table_names():
        print("No templates table — run seed_templates first.")
        return
    if "videos" not in d.table_names():
        print("No videos table — scrape some channels first.")
        return

    # Load all videos once (titles + channel + score)
    all_videos = list(d.query(
        "SELECT v.video_id, v.title, v.channel_id, v.outlier_score, v.views, "
        "       c.name AS channel_name, c.handle AS channel_handle "
        "FROM videos v LEFT JOIN channels c ON c.channel_id = v.channel_id "
        "WHERE v.title IS NOT NULL AND v.video_id IS NOT NULL"
    ))
    print(f"Pool: {len(all_videos)} scraped videos")

    templates = list(d["templates"].rows)
    updated = 0
    now = datetime.now(timezone.utc).isoformat()

    for tpl in templates:
        tpl_id = tpl["id"]
        name = tpl.get("name", "")
        desc = tpl.get("description", "")
        keywords = _tokens(name) | _tokens(desc)
        if not keywords:
            print(f"  · {name}: no keywords, skipping")
            continue

        # Score and pick top
        scored = []
        for v in all_videos:
            s = _score_video(keywords, v.get("title") or "", v.get("outlier_score"))
            if s > 0:
                scored.append((s, v))
        scored.sort(key=lambda x: x[0], reverse=True)

        # Dedupe by video_id, take top N
        picked_ids: list[str] = []
        picked_channels: dict[str, dict] = {}
        seen = set()
        for _, v in scored:
            vid = v.get("video_id")
            if not vid or vid in seen:
                continue
            seen.add(vid)
            picked_ids.append(vid)
            ch_id = v.get("channel_id")
            if ch_id and ch_id not in picked_channels:
                picked_channels[ch_id] = {
                    "name": v.get("channel_name") or "Unknown",
                    "channel_id": ch_id,
                    "handle": v.get("channel_handle") or "",
                }
            if len(picked_ids) >= per_template:
                break

        if not picked_ids:
            print(f"  · {name}: no matches found, skipping")
            continue

        d["templates"].update(tpl_id, {
            "example_video_ids": json.dumps(picked_ids),
            "example_channels": json.dumps(list(picked_channels.values())[:4]),
            "updated_at": now,
        })
        updated += 1
        print(f"  - {name}: {len(picked_ids)} real videos ({', '.join(picked_ids[:3])}…)")

    print(f"\nDone. {updated}/{len(templates)} templates refreshed with real videos.")


if __name__ == "__main__":
    refresh_examples()
