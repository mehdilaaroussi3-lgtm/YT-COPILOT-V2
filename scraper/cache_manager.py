"""Cache manager with TTL-based refresh."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from cli import config as cfg

CACHE_ROOT = Path(cfg.get("defaults.cache_dir", "cache"))
THUMB_DIR = CACHE_ROOT / "thumbnails"
ANALYSIS_DIR = CACHE_ROOT / "analysis"
META_DIR = CACHE_ROOT / "metadata"

for _d in (THUMB_DIR, ANALYSIS_DIR, META_DIR):
    _d.mkdir(parents=True, exist_ok=True)


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def get_cached(path: Path, max_age_seconds: int | None = None) -> dict[str, Any] | None:
    """Return cached JSON if fresh; else None."""
    data = _read_json(path)
    if data is None:
        return None
    if max_age_seconds is not None:
        cached_at = data.get("_cached_at", 0)
        if time.time() - cached_at > max_age_seconds:
            return None
    return data


def set_cached(path: Path, data: dict[str, Any]) -> None:
    payload = {**data, "_cached_at": time.time()}
    _write_json(path, payload)


# TTL constants from masterplan §3.6
TTL_METADATA = 3 * 24 * 3600   # 3 days
TTL_ANALYSIS = 7 * 24 * 3600   # 7 days
TTL_THUMBNAIL = None           # forever
