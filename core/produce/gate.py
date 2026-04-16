"""Review gate: open frames in OS viewer, play VO audio, wait for keypress.

[Enter] → approve section
[R]     → redo section (regenerate images + VO)
[Q]     → quit pipeline
"""
from __future__ import annotations

import os
import platform
import subprocess
import sys
import time
from pathlib import Path

from rich.console import Console

console = Console()


def _open_image(path: Path) -> None:
    if platform.system() == "Windows":
        os.startfile(str(path))
    elif platform.system() == "Darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


def _play_audio(path: Path) -> subprocess.Popen:
    if platform.system() == "Windows":
        return subprocess.Popen(
            ["cmd", "/c", "start", "", str(path)],
            shell=False,
        )
    elif platform.system() == "Darwin":
        return subprocess.Popen(["afplay", str(path)])
    else:
        # Try common Linux players
        for player in ("mpg123", "mpg321", "aplay"):
            if subprocess.run(["which", player], capture_output=True).returncode == 0:
                return subprocess.Popen([player, str(path)],
                                        stdout=subprocess.DEVNULL,
                                        stderr=subprocess.DEVNULL)
    return None


def review(section_id: str, images: list[Path], audios: list[Path]) -> str:
    """Show section artifacts and wait for user decision.

    Returns: 'approve' | 'redo' | 'quit'
    """
    console.print(f"\n[bold cyan]── Review gate: {section_id} ──[/]")
    console.print(f"  {len(images)} frame(s)  |  {len(audios)} VO clip(s)\n")

    # Open all images
    if images:
        console.print("[dim]Opening frames in your image viewer…[/]")
        for img in images:
            _open_image(img)
            time.sleep(0.15)

    # Play VO clips sequentially (best-effort)
    if audios:
        console.print("[dim]Playing VO audio…[/]")
        for audio in audios:
            proc = _play_audio(audio)
            if proc:
                # Wait for this clip to finish before playing next
                try:
                    dur = _probe_duration(audio)
                    time.sleep(min(dur + 0.3, 60.0))
                except Exception:  # noqa: BLE001
                    time.sleep(3.0)

    console.print("\n[bold][[Enter][/bold] Approve   "
                  "[bold][R][/bold] Redo section   "
                  "[bold][Q][/bold] Quit")

    while True:
        try:
            key = input("> ").strip().lower()
        except EOFError:
            return "approve"
        if key in ("", "y", "yes"):
            return "approve"
        if key in ("r", "redo"):
            return "redo"
        if key in ("q", "quit"):
            return "quit"
        console.print("[dim]Enter, R, or Q.[/]")


def _probe_duration(mp3: Path) -> float:
    from core.reverse.ffmpeg_bin import ffprobe_path
    cmd = [ffprobe_path(), "-v", "error",
           "-show_entries", "format=duration",
           "-of", "default=noprint_wrappers=1:nokey=1",
           str(mp3)]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
        return float(out.strip())
    except Exception:  # noqa: BLE001
        return 3.0
