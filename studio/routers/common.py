"""Shared helpers for routers — path normalisation and upload handling."""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import UploadFile

from cli import config as cfg

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = (REPO_ROOT / cfg.get("defaults.output_dir", "output")).resolve()
CACHE_DIR = (REPO_ROOT / cfg.get("defaults.cache_dir", "cache")).resolve()


def _to_url_under(path_like, base: Path, prefix: str) -> str:
    """Convert a filesystem path (absolute OR relative) into a /<prefix>/... URL."""
    if not path_like:
        return ""
    p = Path(str(path_like))
    if not p.is_absolute():
        # Resolve relative paths against the repo root — the pipeline writes
        # with relative paths like "output/2026-...".
        p = (REPO_ROOT / p)
    try:
        rel = p.resolve().relative_to(base)
        return f"/{prefix}/{rel.as_posix()}"
    except (ValueError, OSError):
        # Fallback: text-scan for /<prefix>/ fragment
        s = str(path_like).replace("\\", "/")
        marker = f"/{prefix}/"
        idx = s.find(marker)
        if idx >= 0:
            return s[idx:]
        lower = s.lower()
        if lower.startswith(f"{prefix}/"):
            return "/" + s
        return ""


def to_output_url(path_like) -> str:
    return _to_url_under(path_like, OUTPUT_DIR, "output")


def to_cache_url(path_like) -> str:
    return _to_url_under(path_like, CACHE_DIR, "cache")


async def save_upload(upload: Optional[UploadFile]) -> Optional[Path]:
    if not upload:
        return None
    tmp = Path(tempfile.gettempdir()) / f"thumbcraft_{upload.filename}"
    with tmp.open("wb") as f:
        shutil.copyfileobj(upload.file, f)
    return tmp


def url_to_output_path(url: str) -> Path:
    rel = url.removeprefix("/output/")
    return OUTPUT_DIR / rel
