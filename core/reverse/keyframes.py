"""Stage 4: extract one keyframe pair (mid-scene + ~1s later) per scene."""
from __future__ import annotations

import subprocess
from pathlib import Path

from core.reverse.ffmpeg_bin import ffmpeg_path
from core.reverse.paths import Dirs


def _extract_at(video: Path, t_seconds: float, out: Path) -> None:
    cmd = [
        ffmpeg_path(), "-y",
        "-ss", f"{max(0.0, t_seconds):.3f}",
        "-i", str(video),
        "-frames:v", "1",
        "-q:v", "3",
        str(out),
    ]
    subprocess.run(cmd, capture_output=True, check=True)


def extract_pairs(video: Path, scenes: list[dict], dirs: Dirs) -> None:
    """Write scene_NNNN.jpg (mid-scene) + scene_NNNN_b.jpg (+1s or mid+quarter)."""
    for sc in scenes:
        idx = sc["idx"]
        a = dirs.scene_frame_a(idx)
        b = dirs.scene_frame_b(idx)
        mid = (sc["start"] + sc["end"]) / 2.0
        dur = sc["duration"]
        offset = min(1.0, max(0.2, dur / 4.0))
        t_b = min(sc["end"] - 0.05, mid + offset) if dur > 0.3 else mid
        if not a.exists():
            _extract_at(video, mid, a)
        if not b.exists():
            _extract_at(video, t_b, b)
