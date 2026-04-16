"""Stage 1: download video + captions via yt-dlp."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Callable

from core.reverse.paths import Dirs

Progress = Callable[[str], None]

_URL_ID_RE = re.compile(r"(?:v=|youtu\.be/|shorts/|embed/)([A-Za-z0-9_-]{11})")


def extract_video_id(url: str) -> str:
    m = _URL_ID_RE.search(url)
    if m:
        return m.group(1)
    # fallback: 11-char token
    m = re.search(r"([A-Za-z0-9_-]{11})", url)
    if m:
        return m.group(1)
    raise ValueError(f"Could not extract video id from URL: {url}")


def download(url: str, dirs: Dirs, progress: Progress = lambda _m: None,
             first_seconds: int | None = None) -> dict:
    """Download mp4 + english VTT captions into dirs.tmp.

    Returns basic info dict: {title, channel, uploader, duration}.
    Idempotent: if mp4 already exists it is reused.

    first_seconds: if set, only download that many seconds from the start
    (uses yt-dlp --download-sections, no full video download needed).
    """
    import yt_dlp  # lazy import — heavy dep

    ydl_opts = {
        "format": "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best",
        "merge_output_format": "mp4",
        "outtmpl": str(dirs.tmp / f"{dirs.video_id}.%(ext)s"),
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": ["en", "en-US", "en-GB"],
        "subtitlesformat": "vtt",
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
    }

    if first_seconds:
        ydl_opts["download_ranges"] = yt_dlp.utils.download_range_func(
            None, [(0, first_seconds)]
        )
        ydl_opts["force_keyframes_at_cuts"] = True
        progress(f"downloading first {first_seconds}s of {url}")
    else:
        progress(f"downloading {url}")

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=not dirs.mp4.exists())

    # yt-dlp writes subs as <outtmpl>.<lang>.vtt — copy first one we find to dirs.vtt
    if not dirs.vtt.exists():
        for cand in dirs.tmp.glob(f"{dirs.video_id}*.vtt"):
            cand.replace(dirs.vtt)
            break

    return {
        "title": info.get("title") or "",
        "channel": info.get("channel") or info.get("uploader") or "",
        "channel_id": info.get("channel_id") or "",
        "duration_s": float(info.get("duration") or 0),
        "upload_date": info.get("upload_date") or "",
    }
