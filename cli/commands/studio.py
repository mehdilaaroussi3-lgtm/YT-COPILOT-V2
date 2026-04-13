"""`thumbcraft studio`, `refine`, `profile` commands."""
from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

console = Console()


def studio(
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(8000, "--port"),
) -> None:
    """Launch the local web UI."""
    from studio.server import start_studio
    start_studio(host=host, port=port)


def refine(
    image: Path = typer.Argument(..., exists=True, help="Existing thumbnail to edit"),
    instruction: str = typer.Argument(..., help='e.g. "make it darker, add more grain"'),
) -> None:
    """Apply natural-language edits via Gemini multi-turn."""
    from generators.refiner import refine_thumbnail
    console.print(f"[cyan]Refining[/] {image}")
    out = refine_thumbnail(image, instruction)
    console.print(f"[green]✓[/] Saved: [cyan]{out}[/]")


def profile_list() -> None:
    """List available channel profiles."""
    from core.profile_loader import list_profiles
    for p in list_profiles():
        console.print(f"  • [cyan]{p['key']}[/] — {p['name']}  [dim]({p['niche']})[/]")
