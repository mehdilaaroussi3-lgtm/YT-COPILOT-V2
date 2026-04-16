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
    # Last scan timestamp: max of last_scanned across all channels
    last_scan_at: str | None = None
    try:
        row = d.execute("SELECT MAX(last_scanned) FROM channels WHERE last_scanned IS NOT NULL").fetchone()
        if row and row[0]:
            last_scan_at = row[0]
    except Exception:  # noqa: BLE001
        pass

    from studio.routers.common import CACHE_DIR, OUTPUT_DIR
    return {
        "session": session_stats.snapshot(),
        "db_rows": counts,
        "last_scan_at": last_scan_at,
        "disk": {
            "cache_mb": round(_dir_size(CACHE_DIR) / 1_000_000, 1),
            "output_mb": round(_dir_size(OUTPUT_DIR) / 1_000_000, 1),
        },
    }


@router.get("/api/home/latest-creations")
def latest_creations(limit: int = 4) -> dict:
    """Return the most recently modified thumbnails from productions + reverse folders.

    Used by Home "Your Latest Creations" showcase.
    """
    from pathlib import Path
    roots = [Path("data/productions"), Path("data/reverse"), Path("data/lab")]
    candidates: list[tuple[float, Path]] = []
    for root in roots:
        if not root.exists():
            continue
        for p in root.rglob("*.png"):
            try:
                if p.stat().st_size < 10_000:  # skip tiny/broken
                    continue
                candidates.append((p.stat().st_mtime, p))
            except OSError:
                continue
        for p in root.rglob("*.jpg"):
            try:
                if p.stat().st_size < 10_000:
                    continue
                candidates.append((p.stat().st_mtime, p))
            except OSError:
                continue

    candidates.sort(key=lambda x: x[0], reverse=True)
    items = []
    data_root = Path("data")
    for mtime, p in candidates[:limit]:
        try:
            rel = p.relative_to(data_root)
        except ValueError:
            continue
        url = "/data/" + str(rel).replace("\\", "/")
        # Pretty name: parent folder (e.g. production slug or reverse video title)
        source = p.parts[1] if len(p.parts) > 1 else "unknown"  # e.g. "productions", "reverse", "lab"
        items.append({
            "url": url,
            "name": p.parent.name,
            "source": source,
            "filename": p.name,
            "mtime": mtime,
        })
    return {"items": items}


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
