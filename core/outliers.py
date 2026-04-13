"""Helpers for reading outlier thumbnails out of the SQLite DB for the UI.

Home page calls `random_outliers()`. Search hits `search_outliers()`.
Both union:
  (a) videos from curated channels_registry.yml that happened to be scanned
  (b) videos from user-added `tracked_channels`
— so the home feed reflects everything the user has in their local index.
"""
from __future__ import annotations

import random
from typing import Any

from data.db import db


def _hydrate(row: dict, d) -> dict:
    vid = row["video_id"]
    thumb = d["thumbnails"].get(vid) if vid in d["thumbnails"].pks else None
    channel = None
    if row.get("channel_id") and row["channel_id"] in d["channels"].pks:
        channel = d["channels"].get(row["channel_id"])
    elif row.get("channel_id") and row["channel_id"] in d["tracked_channels"].pks:
        channel = d["tracked_channels"].get(row["channel_id"])
    return {
        "video_id": vid,
        "title": row.get("title", ""),
        "views": row.get("views", 0),
        "outlier_score": row.get("outlier_score", 0),
        "published_at": row.get("published_at", ""),
        "channel_id": row.get("channel_id", ""),
        "channel_name": (channel or {}).get("name", ""),
        "thumbnail_path": (thumb or {}).get("file_path", ""),
        "style_tags": (thumb or {}).get("style_tags", ""),
    }


def random_outliers(limit: int = 12, min_score: float = 2.0) -> list[dict[str, Any]]:
    d = db()
    rows = list(d["videos"].rows_where(
        "outlier_score >= ?", [min_score],
        order_by="outlier_score desc",
    ))
    if not rows:
        return []
    random.shuffle(rows)
    return [_hydrate(r, d) for r in rows[:limit]]


def search_outliers(query: str = "", niche: str | None = None,
                    channel_id: str | None = None,
                    limit: int = 60) -> list[dict[str, Any]]:
    d = db()
    clauses = ["outlier_score >= 1"]
    args: list = []
    if query:
        clauses.append("LOWER(title) LIKE ?")
        args.append(f"%{query.lower()}%")
    if channel_id:
        clauses.append("channel_id = ?")
        args.append(channel_id)

    where = " AND ".join(clauses)
    rows = list(d["videos"].rows_where(where, args,
                                        order_by="outlier_score desc",
                                        limit=limit))
    hydrated = [_hydrate(r, d) for r in rows]
    if niche:
        # Soft filter: keep rows whose channel niche matches (if we have it)
        d2 = db()
        niched_ids = {r["channel_id"] for r in d2["channels"].rows_where(
            "niche = ?", [niche]
        )}
        hydrated = [h for h in hydrated if h["channel_id"] in niched_ids or not h["channel_id"]]
    return hydrated


def get_outlier(video_id: str) -> dict | None:
    d = db()
    if video_id not in d["videos"].pks:
        return None
    return _hydrate(d["videos"].get(video_id), d)
