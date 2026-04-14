"""`thumbcraft generate` — full 3-variant pipeline."""
from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from generators.pipeline import run_pipeline

console = Console()


def generate(
    title: str = typer.Argument(..., help="Video title."),
    channel: str = typer.Option("default", "--channel", "-c", help="Channel profile name."),
    script: str = typer.Option(None, "--script", help="Inline script excerpt."),
    script_file: Path = typer.Option(None, "--script-file", exists=True),
    sketch: Path = typer.Option(None, "--sketch", exists=True,
                                help="Rough composition sketch as reference."),
    reference: Path = typer.Option(None, "--reference", exists=True,
                                    help="Style reference image."),
    no_text: bool = typer.Option(False, "--no-text", help="Skip text overlay on all variants."),
    variants: int = typer.Option(3, "--variants", help="Number of variants (1-3)."),
    no_mockup: bool = typer.Option(False, "--no-mockup"),
    no_quality: bool = typer.Option(False, "--no-quality", help="Skip Vision quality gate."),
) -> None:
    script_text = script
    if script_file:
        script_text = script_file.read_text(encoding="utf-8")

    console.print(f"[bold cyan]YTcopilot[/] generating: [yellow]{title}[/]")

    def progress(msg: str) -> None:
        console.print(f"[dim]→ {msg}[/]")

    try:
        result = run_pipeline(
            title=title, channel=channel,
            script=script_text, sketch=sketch, reference=reference,
            no_text=no_text, variants=variants,
            do_mockup=not no_mockup, do_quality=not no_quality,
            on_progress=progress,
        )
    except Exception as e:  # noqa: BLE001
        console.print(f"[bold red]✗ Pipeline failed:[/] {e}")
        raise typer.Exit(1)

    console.print(f"\n[bold green]✓ Done.[/] Output: [cyan]{result.output_dir}[/]")
    console.print(f"  Hook: [bold]{result.text_hook}[/]  "
                  f"(pairing score: {result.pairing_score}/10)")
    for v in result.variants:
        score_str = f"{v.score:.1f}/10" if v.score is not None else "—"
        console.print(f"  Variant {v.variant}: [cyan]{v.file_path}[/]  [dim](score {score_str})[/]")
    if result.mockup_dark:
        console.print(f"  Mockup (dark): [cyan]{result.mockup_dark}[/]")
        console.print(f"  Mockup (light): [cyan]{result.mockup_light}[/]")
