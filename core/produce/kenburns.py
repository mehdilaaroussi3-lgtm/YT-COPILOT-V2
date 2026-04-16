"""Stage 3c: Ken Burns clip renderer.

Converts a still PNG → video clip with zoompan motion at the target
resolution. Duration is set by the VO audio duration — zero fixed durations.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from core.reverse.ffmpeg_bin import ffmpeg_path

FPS = 60


def _zoompan_expr(camera_move: str, fps: int, duration_s: float) -> tuple[str, str, str]:
    """Return (z_expr, x_expr, y_expr) for ffmpeg zoompan filter."""
    n_frames = int(duration_s * fps)

    # How fast to zoom per frame — travel full zoom range over clip duration
    # Start zoom: 1.0 (fit), end zoom: ~1.2 for dolly moves
    z_step = 0.2 / max(n_frames, 1)

    m = camera_move or "static"
    if m == "dolly_in":
        z = f"zoom+{z_step:.6f}"
        x = "iw/2-(iw/zoom/2)"
        y = "ih/2-(ih/zoom/2)"
    elif m == "dolly_out":
        z = f"if(lte(zoom,1.0),1.2,max(1.001,zoom-{z_step:.6f}))"
        x = "iw/2-(iw/zoom/2)"
        y = "ih/2-(ih/zoom/2)"
    elif m == "pan_left":
        z = "1.15"
        x = f"x+{max(1, int(0.3 * 1920 / max(n_frames, 1)))}"
        y = "ih/2-(ih/zoom/2)"
    elif m == "pan_right":
        x_step = max(1, int(0.3 * 1920 / max(n_frames, 1)))
        z = "1.15"
        x = f"if(lte(x,0),iw/zoom,x-{x_step})"
        y = "ih/2-(ih/zoom/2)"
    elif m == "tilt_up":
        z = "1.15"
        x = "iw/2-(iw/zoom/2)"
        y_step = max(1, int(0.3 * 1080 / max(n_frames, 1)))
        y = f"y+{y_step}"
    elif m == "tilt_down":
        z = "1.15"
        x = "iw/2-(iw/zoom/2)"
        y_step = max(1, int(0.3 * 1080 / max(n_frames, 1)))
        y = f"if(lte(y,0),ih/zoom,y-{y_step})"
    elif m == "orbit":
        # Simulate orbit with a gentle pan + slight zoom
        z = f"zoom+{z_step * 0.5:.6f}"
        x_step = max(1, int(0.15 * 1920 / max(n_frames, 1)))
        x = f"x+{x_step}"
        y = "ih/2-(ih/zoom/2)"
    else:  # static / unknown
        z = "1.0"
        x = "iw/2-(iw/zoom/2)"
        y = "ih/2-(ih/zoom/2)"

    return z, x, y


def render(
    image_path: Path,
    vo_path: Path,
    out_path: Path,
    duration_s: float,
    camera_move: str,
    width: int,
    height: int,
) -> Path:
    """Render Ken Burns clip. Duration comes from VO duration — exact sync.

    Args:
        image_path: source PNG/JPEG still
        vo_path: VO mp3 (mixed into output clip)
        out_path: destination .mp4
        duration_s: exact duration from VO audio
        camera_move: one of dolly_in|dolly_out|pan_left|pan_right|tilt_up|tilt_down|static|orbit
        width, height: target resolution (e.g. 3840×2160 for 4K)
    """
    if out_path.exists():
        return out_path

    fps = FPS
    n_frames = max(1, int(duration_s * fps))
    z, x, y = _zoompan_expr(camera_move, fps, duration_s)

    # Scale source image up to target res + zoompan headroom
    # zoompan needs source larger than output so it can pan/zoom
    scale_w = int(width * 1.25)
    scale_h = int(height * 1.25)

    zoompan = (
        f"zoompan=z='{z}':x='{x}':y='{y}'"
        f":d={n_frames}:s={width}x{height}:fps={fps}"
    )

    cmd = [
        ffmpeg_path(), "-y",
        "-loop", "1", "-i", str(image_path),
        "-i", str(vo_path),
        "-filter_complex",
        f"[0:v]scale={scale_w}:{scale_h},{zoompan}[v]",
        "-map", "[v]",
        "-map", "1:a",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k",
        "-t", f"{duration_s:.3f}",
        "-pix_fmt", "yuv420p",
        str(out_path),
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return out_path
