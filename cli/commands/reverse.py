"""`thumbcraft reverse` — Ultimate Reverse Engineer.

Dissects a YouTube video into a picture-perfect production blueprint.
Isolated from all other tools; safe to run alongside existing commands.
"""
from __future__ import annotations

import typer
from rich.console import Console

from cli import config as cfg
from core.reverse import reverse as run_reverse

console = Console()


def reverse(
    url: str = typer.Argument(..., help="YouTube video URL."),
    force: bool = typer.Option(False, "--force", help="Re-run all stages."),
    force_stage: str = typer.Option(
        None, "--force-stage",
        help="Re-run one stage: download|probe|scenes|keyframes|motion|vision|classify|transcript|audio|script_formula|blueprint",
    ),
    max_scenes: int = typer.Option(None, "--max-scenes", help="Cap scenes analyzed (evenly sampled)."),
    no_whisper: bool = typer.Option(False, "--no-whisper", help="Disable Whisper transcript fallback."),
    confirm_long: bool = typer.Option(False, "--confirm", help="Confirm processing for long videos."),
    first: int = typer.Option(None, "--first", help="Only process the first N seconds (no full download)."),
) -> None:
    """Reverse-engineer a YouTube video into a blueprint."""
    console.print(f"[bold cyan]Ultimate Reverse Engineer[/] → [yellow]{url}[/]")

    def progress(msg: str) -> None:
        console.print(f"[dim]→ {msg}[/]")

    # Long-video warning (no hard cap per plan)
    warn_min = int(cfg.get("reverse.long_video_warn_min") or 30)

    try:
        out = run_reverse(
            url,
            force=force,
            force_stage=force_stage,
            max_scenes=max_scenes,
            whisper_enabled=(not no_whisper),
            first_seconds=first,
            progress=progress,
        )
    except Exception as e:  # noqa: BLE001
        console.print(f"[bold red]✗ failed:[/] {e}")
        raise typer.Exit(code=1)

    console.print(f"[bold green]✓[/] blueprint written to [cyan]{out}[/]")
    console.print(f"  blueprint.json  → {out / 'blueprint.json'}")
    console.print(f"  scenes.json     → {out / 'scenes.json'}")
    console.print(f"  frames/         → {out / 'frames'}")
    _ = warn_min  # reserved for future interactive confirm
    _ = confirm_long
