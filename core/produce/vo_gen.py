"""Stage 3b: per-scene VO generation via ElevenLabs + duration measurement."""
from __future__ import annotations

import subprocess
from pathlib import Path

from core.produce.elevenlabs import generate_vo
from core.reverse.ffmpeg_bin import ffprobe_path


def render(text: str, voice_id: str, out_path: Path, force: bool = False) -> float:
    """Generate VO mp3, save to out_path, return duration in seconds."""
    if force or not out_path.exists():
        mp3_bytes = generate_vo(text, voice_id)
        out_path.write_bytes(mp3_bytes)
    return probe_duration(out_path)


def probe_duration(mp3: Path) -> float:
    """Return audio duration in seconds via ffprobe."""
    cmd = [
        ffprobe_path(), "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(mp3),
    ]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
        return float(out.strip())
    except Exception:  # noqa: BLE001
        return 4.0  # safe fallback
