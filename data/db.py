"""SQLite database layer for YTcopilot.

Stores: channels, videos, thumbnails, style_index, title_patterns,
trends, generations, research findings.
"""
from __future__ import annotations

from pathlib import Path

import sqlite_utils

DB_PATH = Path(__file__).resolve().parent / "thumbcraft.db"


def db() -> sqlite_utils.Database:
    """Return a Database handle with all tables ensured."""
    d = sqlite_utils.Database(DB_PATH)
    _ensure_schema(d)
    return d


def _ensure_schema(d: sqlite_utils.Database) -> None:
    if "channels" not in d.table_names():
        d["channels"].create({
            "channel_id": str,
            "name": str,
            "subs": int,
            "median_views": float,
            "niche": str,
            "last_scanned": str,
        }, pk="channel_id")

    if "videos" not in d.table_names():
        d["videos"].create({
            "video_id": str,
            "channel_id": str,
            "title": str,
            "views": int,
            "outlier_score": float,
            "published_at": str,
            "fetched_at": str,
        }, pk="video_id")
        d["videos"].create_index(["channel_id"])
        d["videos"].create_index(["outlier_score"])

    if "thumbnails" not in d.table_names():
        d["thumbnails"].create({
            "video_id": str,
            "file_path": str,
            "description": str,    # Gemini Vision description
            "style_tags": str,     # comma-joined
            "colors": str,         # JSON list of hex codes
            "text_amount": str,    # none/minimal/heavy
            "analyzed_at": str,
        }, pk="video_id")

    if "title_patterns" not in d.table_names():
        d["title_patterns"].create({
            "id": int,
            "niche": str,
            "pattern": str,
            "frequency": int,
            "avg_outlier_score": float,
            "examples": str,       # JSON list
        }, pk="id")
        d["title_patterns"].create_index(["niche"])

    if "trends" not in d.table_names():
        d["trends"].create({
            "id": int,
            "niche": str,
            "style_tag": str,
            "week": str,           # ISO week start date
            "frequency": int,
            "direction": str,      # rising / falling / flat
        }, pk="id")

    if "generations" not in d.table_names():
        d["generations"].create({
            "id": int,
            "title": str,
            "channel": str,
            "niche": str,
            "variant": str,
            "file_path": str,
            "prompt": str,
            "references_used": str,  # JSON
            "score": float,
            "cost_usd": float,
            "created_at": str,
        }, pk="id")

    # --- v2: folders, bookmarks, tracked channels, ideas, titles ----
    if "folders" not in d.table_names():
        d["folders"].create({
            "id": int,
            "name": str,
            "color": str,           # hex accent for UI
            "created_at": str,
        }, pk="id")

    if "bookmarks" not in d.table_names():
        d["bookmarks"].create({
            "id": int,
            "folder_id": int,
            "source": str,          # 'reference' | 'generated'
            "video_id": str,        # populated when source='reference' (FK videos)
            "generation_id": int,   # populated when source='generated' (FK generations)
            "note": str,
            "added_at": str,
        }, pk="id")
        d["bookmarks"].create_index(["folder_id"])

    if "tracked_channels" not in d.table_names():
        d["tracked_channels"].create({
            "channel_id": str,
            "handle": str,
            "name": str,
            "subs": int,
            "description": str,     # raw YouTube channel description
            "ai_summary": str,       # AI-synthesized smart summary
            "avatar_url": str,
            "is_default": int,       # 0 / 1 — one channel can be the default
            "added_at": str,
            "last_scanned": str,
            "niche_override": str,
        }, pk="channel_id")
    else:
        # Back-compat — add new columns if missing
        cols = {c.name for c in d["tracked_channels"].columns}
        for col in ("description", "avatar_url", "is_default", "ai_summary"):
            if col not in cols:
                d["tracked_channels"].add_column(
                    col, int if col == "is_default" else str,
                )

    if "generated_ideas" not in d.table_names():
        d["generated_ideas"].create({
            "id": int,
            "channel": str,
            "topic": str,
            "idea_title": str,
            "idea_description": str,
            "created_at": str,
            "batch_id": str,        # groups ideas generated together
        }, pk="id")
        d["generated_ideas"].create_index(["channel"])
        d["generated_ideas"].create_index(["batch_id"])

    if "generated_titles" not in d.table_names():
        d["generated_titles"].create({
            "id": int,
            "channel": str,
            "source_idea": str,
            "title": str,
            "char_count": int,
            "created_at": str,
            "batch_id": str,
            "pinned": int,          # 0 / 1
        }, pk="id")
        d["generated_titles"].create_index(["channel"])
        d["generated_titles"].create_index(["batch_id"])

    if "research" not in d.table_names():
        d["research"].create({
            "id": int,
            "source": str,         # e.g. "1of10 blog"
            "url": str,
            "title": str,
            "summary": str,
            "key_findings": str,   # JSON
            "published_at": str,
            "fetched_at": str,
        }, pk="id")
