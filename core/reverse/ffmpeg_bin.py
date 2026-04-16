"""Resolve bundled ffmpeg/ffprobe binaries via imageio-ffmpeg."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def ffmpeg_path() -> str:
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


@lru_cache(maxsize=1)
def ffprobe_path() -> str:
    # imageio-ffmpeg doesn't ship ffprobe, but on Windows it ships ffmpeg
    # which can do most probing via `ffmpeg -i`. We still prefer ffprobe
    # when it's available on PATH; otherwise fall back to ffmpeg.
    import shutil
    p = shutil.which("ffprobe")
    return p or ffmpeg_path()
