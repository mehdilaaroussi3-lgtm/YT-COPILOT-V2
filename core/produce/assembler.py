"""Stage 4+5: section assembly and final video assembly.

Section assembly: concat all scene clips (each already has VO baked in)
into one section.mp4.

Final assembly: concat all section.mp4 files → output/final_<res>.mp4.
Optional music bed mixed under VO at configurable duck level.
"""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from cli import config as cfg
from core.reverse.ffmpeg_bin import ffmpeg_path


def assemble_section(scene_clips: list[Path], out: Path) -> Path:
    """Concat scene clips (each has VO) into one section video."""
    if out.exists():
        return out
    if len(scene_clips) == 1:
        # Single scene — just copy
        cmd = [ffmpeg_path(), "-y", "-i", str(scene_clips[0]),
               "-c", "copy", str(out)]
        subprocess.run(cmd, capture_output=True, check=True)
        return out

    # Write concat list to temp file
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False,
                                     encoding="utf-8") as f:
        for clip in scene_clips:
            f.write(f"file '{clip.as_posix()}'\n")
        list_path = f.name

    cmd = [
        ffmpeg_path(), "-y",
        "-f", "concat", "-safe", "0",
        "-i", list_path,
        "-c", "copy",
        str(out),
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return out


def assemble_final(section_videos: list[Path], out: Path,
                   music_path: Path | None = None) -> Path:
    """Concat all section.mp4s into final video, optionally mixing music bed."""
    if out.exists():
        out.unlink()

    if len(section_videos) == 1 and music_path is None:
        cmd = [ffmpeg_path(), "-y", "-i", str(section_videos[0]),
               "-c", "copy", str(out)]
        subprocess.run(cmd, capture_output=True, check=True)
        return out

    # Write concat list
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False,
                                     encoding="utf-8") as f:
        for sv in section_videos:
            f.write(f"file '{sv.as_posix()}'\n")
        list_path = f.name

    if music_path is None:
        cmd = [
            ffmpeg_path(), "-y",
            "-f", "concat", "-safe", "0", "-i", list_path,
            "-c", "copy", str(out),
        ]
        subprocess.run(cmd, capture_output=True, check=True)
        return out

    # Mix music bed under VO
    duck = float(cfg.get("produce.music_duck_level") or 0.15)
    # First produce a silent-concat video, then re-encode with mixed audio
    concat_out = out.with_suffix(".concat.mp4")
    cmd = [
        ffmpeg_path(), "-y",
        "-f", "concat", "-safe", "0", "-i", list_path,
        "-c", "copy", str(concat_out),
    ]
    subprocess.run(cmd, capture_output=True, check=True)

    # Probe video duration for music loop
    cmd2 = [ffmpeg_path(), "-y",
            "-i", str(concat_out),
            "-stream_loop", "-1",   # loop music
            "-i", str(music_path),
            "-filter_complex",
            f"[1:a]volume={duck}[music];"
            f"[0:a][music]amix=inputs=2:duration=first:dropout_transition=2[a]",
            "-map", "0:v", "-map", "[a]",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            str(out)]
    subprocess.run(cmd2, capture_output=True, check=True)
    concat_out.unlink(missing_ok=True)
    return out
