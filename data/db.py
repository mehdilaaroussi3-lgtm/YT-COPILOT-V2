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

    # --- My Channels workspace tables ----
    if "my_channels" not in d.table_names():
        d["my_channels"].create({
            "name": str,               # user-given channel name (pk)
            "niche": str,
            "reference_yt_url": str,
            "reference_channel_name": str,
            "reference_channel_id": str,
            "dna_path": str,
            "logo_path": str,
            "avatar_color": str,
            "target_audience": str,    # e.g. "25-35 men into finance"
            "tone": str,               # educational | shocking | entertaining | mix
            "voice_id": str,           # ElevenLabs voice ID for this channel
            "default_duration": str,   # default video length hint e.g. "10min"
            "created_at": str,
        }, pk="name")
    else:
        # Back-compat — add new columns if missing
        mc_cols = {c.name for c in d["my_channels"].columns}
        for col, typ in [("reference_channel_id", str), ("logo_path", str),
                         ("target_audience", str), ("tone", str),
                         ("voice_id", str), ("default_duration", str)]:
            if col not in mc_cols:
                d["my_channels"].add_column(col, typ, not_null_default="")

    if "channel_videos" not in d.table_names():
        d["channel_videos"].create({
            "id": int,
            "channel_name": str,
            "topic": str,
            "brief": str,              # optional angle/brief before script gen
            "status": str,             # idea | thumbnail | scripted | producing | done
            "thumbnail_path": str,     # generated thumbnail PNG
            "script_json": str,        # JSON string of approved script
            "script_status": str,      # none | generating | ready | approved
            "blueprint_path": str,
            "production_name": str,
            "final_mp4_path": str,
            "duration_hint": str,
            "resolution": str,
            "created_at": str,
        }, pk="id")
        d["channel_videos"].create_index(["channel_name"])
    else:
        # Back-compat
        cv_cols = {c.name for c in d["channel_videos"].columns}
        for col, typ in [("brief", str), ("thumbnail_path", str),
                         ("script_json", str), ("script_status", str)]:
            if col not in cv_cols:
                d["channel_videos"].add_column(col, typ, not_null_default="")

    # --- Production Pipeline indexing table ----
    if "productions" not in d.table_names():
        d["productions"].create({
            "name": str,
            "blueprint_path": str,
            "topic": str,
            "resolution": str,
            "voice_id": str,
            "section_count": int,
            "status": str,
            "created_at": str,
        }, pk="name")

    # --- Ultimate Reverse Engineer (URE) indexing tables ----
    if "reverse_videos" not in d.table_names():
        d["reverse_videos"].create({
            "video_id": str,
            "url": str,
            "title": str,
            "channel": str,
            "duration_s": float,
            "production_formula": str,
            "scenes_count": int,
            "processed_at": str,
        }, pk="video_id")

    if "reverse_scenes" not in d.table_names():
        d["reverse_scenes"].create({
            "id": int,
            "video_id": str,
            "idx": int,
            "start_s": float,
            "end_s": float,
            "production_type": str,
            "shot_type": str,
            "keyframe_path": str,
        }, pk="id")
        d["reverse_scenes"].create_index(["video_id"])

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

    # --- Custom Styles (for unified style system) ----
    if "styles" not in d.table_names():
        d["styles"].create({
            "id": str,                    # PK: "custom:<uuid4>"
            "style_type": str,            # always "custom"
            "name": str,
            "description": str,
            "image_prompt_prefix": str,   # for presets / custom
            "style_brief": str,           # Gemini-generated or user-provided
            "image_paths": str,           # JSON array of file paths
            "preview_image_path": str,    # path to auto-generated preview PNG
            "created_at": str,
            "updated_at": str,
        }, pk="id")
    else:
        # Back-compat — add preview_image_path column if missing
        styles_cols = {c.name for c in d["styles"].columns}
        if "preview_image_path" not in styles_cols:
            d["styles"].add_column("preview_image_path", str, not_null_default="")

    # --- Content Format Templates ----
    if "templates" not in d.table_names():
        d["templates"].create({
            "id": str,                     # PK: 12-char UUID hex
            "name": str,                   # e.g. "Your Life As A..."
            "description": str,            # optional user description
            "status": str,                 # draft | analyzing | ready | error
            "stage": str,                  # current analysis stage label
            "stage_pct": int,              # 0-100 progress percentage
            "example_channels": str,       # JSON [{name, channel_id, handle}]
            "example_video_ids": str,      # JSON [video_id, ...] for thumb strip
            "dna_path": str,               # path to data/templates/<id>/dna.json
            "reddit_findings": str,        # JSON {tips, success_patterns, posts}
            "prompt_helpers": str,         # JSON {hook_formulas, script_structure_prompt, image_prompt_prefix}
            "error": str,                  # error message if status == "error"
            "created_at": str,
            "updated_at": str,
        }, pk="id")
    else:
        # Back-compat — add new columns if missing
        t_cols = {c.name for c in d["templates"].columns}
        for col, typ in [("stage", str), ("stage_pct", int), ("reddit_findings", str),
                         ("prompt_helpers", str), ("error", str)]:
            if col not in t_cols:
                d["templates"].add_column(col, typ, not_null_default="" if typ == str else 0)
