"""Stage 2: probe video for duration, fps, resolution."""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from core.reverse.ffmpeg_bin import ffmpeg_path, ffprobe_path


def probe(video: Path) -> dict:
    """Return {duration_s, fps, width, height} for the given mp4."""
    ffprobe = ffprobe_path()
    if Path(ffprobe).name.lower().startswith("ffprobe"):
        cmd = [
            ffprobe, "-v", "error", "-print_format", "json",
            "-show_streams", "-show_format", str(video),
        ]
        out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
        data = json.loads(out)
        vs = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), {})
        num, den = (vs.get("r_frame_rate") or "0/1").split("/")
        fps = float(num) / float(den) if float(den) else 0.0
        return {
            "duration_s": float(data.get("format", {}).get("duration") or 0.0),
            "fps": fps,
            "width": int(vs.get("width") or 0),
            "height": int(vs.get("height") or 0),
        }

    # Fallback: parse `ffmpeg -i` stderr
    cmd = [ffmpeg_path(), "-i", str(video)]
    res = subprocess.run(cmd, capture_output=True, text=True)
    err = res.stderr
    dur = 0.0
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.?\d*)", err)
    if m:
        h, mi, s = m.groups()
        dur = int(h) * 3600 + int(mi) * 60 + float(s)
    fps = 0.0
    m = re.search(r"(\d+(?:\.\d+)?)\s*fps", err)
    if m:
        fps = float(m.group(1))
    w = h = 0
    m = re.search(r"(\d{3,4})x(\d{3,4})", err)
    if m:
        w, h = int(m.group(1)), int(m.group(2))
    return {"duration_s": dur, "fps": fps, "width": w, "height": h}
