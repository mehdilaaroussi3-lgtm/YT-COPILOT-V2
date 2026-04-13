"""/api/settings, /api/stats — local config surface."""
from __future__ import annotations

import os
import sys
from pathlib import Path

from fastapi import APIRouter

from cli import config as cfg
from core import session_stats
from data.db import db

router = APIRouter()


def _mask(s: str | None) -> str:
    if not s:
        return ""
    if len(s) < 10:
        return "•" * len(s)
    return s[:4] + "•" * (len(s) - 8) + s[-4:]


def _dir_size(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


@router.get("/api/settings")
def settings() -> dict:
    vertex_key = cfg.get("vertex.api_key", "")
    yt_key = cfg.get("youtube.api_key", "")
    return {
        "models": {
            "image": cfg.get("gemini.image_model"),
            "vision": cfg.get("gemini.vision_model"),
            "image_size": cfg.get("gemini.image_size"),
            "aspect_ratio": cfg.get("gemini.aspect_ratio"),
        },
        "keys": {
            "vertex_masked": _mask(vertex_key),
            "youtube_masked": _mask(yt_key),
        },
        "paths": {
            "output_dir": cfg.get("defaults.output_dir"),
            "cache_dir": cfg.get("defaults.cache_dir"),
        },
    }


@router.get("/api/stats")
def stats() -> dict:
    d = db()
    counts = {
        "channels_registry": d["channels"].count,
        "videos_indexed": d["videos"].count,
        "thumbnails_cached": d["thumbnails"].count,
        "generations": d["generations"].count,
        "folders": d["folders"].count,
        "bookmarks": d["bookmarks"].count,
        "tracked_channels": d["tracked_channels"].count,
        "generated_ideas": d["generated_ideas"].count,
        "generated_titles": d["generated_titles"].count,
    }
    from studio.routers.common import CACHE_DIR, OUTPUT_DIR
    return {
        "session": session_stats.snapshot(),
        "db_rows": counts,
        "disk": {
            "cache_mb": round(_dir_size(CACHE_DIR) / 1_000_000, 1),
            "output_mb": round(_dir_size(OUTPUT_DIR) / 1_000_000, 1),
        },
    }


@router.post("/api/settings/open-output")
def open_output_folder() -> dict:
    """Open the output folder in the OS file browser."""
    from studio.routers.common import OUTPUT_DIR
    try:
        if sys.platform == "win32":
            os.startfile(str(OUTPUT_DIR))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            os.system(f'open "{OUTPUT_DIR}"')
        else:
            os.system(f'xdg-open "{OUTPUT_DIR}"')
        return {"ok": True}
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)}
