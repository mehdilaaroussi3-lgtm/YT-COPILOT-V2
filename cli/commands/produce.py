"""`thumbcraft produce` — Production Pipeline.

Consumes a URE blueprint.json and produces a finished MP4 in the same
style, applied to a new topic. VO audio drives all timing — zero drift.
"""
from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from core.produce.pipeline import produce as run_produce

console = Console()

RESOLUTIONS = ["4K", "2K", "1080p"]


def produce(
    blueprint: Path = typer.Argument(
        ..., help="Path to blueprint.json from `thumbcraft reverse`.", exists=True
    ),
    topic: str = typer.Option(..., "--topic", "-t", help="New video topic."),
    name: str = typer.Option(..., "--name", "-n", help="Project name (used as folder name)."),
    resolution: str = typer.Option(
        "4K", "--resolution", "-r",
        help="Output resolution: 4K | 2K | 1080p.",
    ),
    duration: str = typer.Option(
        "10min", "--duration", "-d",
        help="Target video duration hint: e.g. 10min, 5:30, 300s.",
    ),
    voice: str = typer.Option(
        None, "--voice", help="ElevenLabs voice ID. Omit to pick interactively."
    ),
    redo_section: str = typer.Option(
        None, "--redo-section",
        help="Re-run one section by ID (e.g. hook, section_01, closer).",
    ),
    no_gate: bool = typer.Option(
        False, "--no-gate", help="Skip review gates — run straight to final assembly."
    ),
    music: Path = typer.Option(
        None, "--music", help="Optional music bed (mp3/wav) to mix under VO.",
        exists=False,
    ),
    thumbnail_channel: str = typer.Option(
        None, "--thumbnail-channel", "--tc",
        help=(
            "YouTube @handle or channel URL to use as the thumbnail style target. "
            "When provided, a channel-style thumbnail is generated as the final step. "
            "Persisted in project.json — only needed on the first run."
        ),
    ),
) -> None:
    """Produce a video in the style of a reversed blueprint."""
    if resolution not in RESOLUTIONS:
        console.print(f"[red]Invalid resolution '{resolution}'. Choose: {', '.join(RESOLUTIONS)}[/]")
        raise typer.Exit(1)

    console.print(f"[bold cyan]Production Pipeline[/]  [dim]{name}[/]")
    console.print(f"  Topic      : [yellow]{topic}[/]")
    console.print(f"  Blueprint  : {blueprint}")
    console.print(f"  Resolution : {resolution}  |  Target: {duration}\n")

    def progress(msg: str) -> None:
        console.print(f"[dim]→ {msg}[/]")

    try:
        final = run_produce(
            blueprint_path=blueprint,
            name=name,
            topic=topic,
            resolution=resolution,
            duration_hint=duration,
            voice_id=voice,
            redo_section=redo_section,
            no_gate=no_gate,
            music_path=music,
            thumbnail_channel=thumbnail_channel or None,
            progress=progress,
        )
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        console.print(f"[bold red]✗ failed:[/] {e}")
        raise typer.Exit(code=1)

    console.print(f"\n[bold green]✓ done[/] → [cyan]{final}[/]")
