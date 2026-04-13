"""`thumbcraft scrape`, `refs`, `analyze`, `registry` commands."""
from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from scraper.pipeline import get_or_build_style_brief, scrape_niche
from scraper.registry_manager import list_niches, load_registry
from scraper.thumbnail_analyzer import analyze_thumbnails

console = Console()


def scrape(
    niche: str = typer.Option(..., "--niche", "-n", help="Niche key from channels_registry.yml"),
    per_channel: int = typer.Option(10, "--per-channel", help="Top videos per channel"),
    min_score: float = typer.Option(5.0, "--min-score", help="Minimum outlier score"),
    refresh: bool = typer.Option(False, "--refresh", help="Bypass cache"),
) -> None:
    """Scrape outlier thumbnails for a niche."""
    console.print(f"[bold cyan]Scraping niche:[/] {niche}")
    result = scrape_niche(niche, per_channel=per_channel,
                          min_outlier_score=min_score, refresh=refresh)

    table = Table(title=f"Outliers found in '{niche}'")
    table.add_column("Channel", style="cyan")
    table.add_column("Title", overflow="fold")
    table.add_column("Views", justify="right")
    table.add_column("Outlier", justify="right", style="green")
    table.add_column("Thumb", style="dim")

    for o in result["outliers"][:30]:
        title = o.get("snippet", {}).get("title", "")[:60]
        views = int(o.get("statistics", {}).get("viewCount", 0))
        score = o.get("outlier_score", 0)
        thumb = "✓" if o.get("thumbnail_path") else "✗"
        table.add_row(o.get("channel_name", ""), title, f"{views:,}",
                      f"{score}x", thumb)

    console.print(table)
    console.print(f"\n[green]✓[/] Total outliers: {len(result['outliers'])}")
    console.print("[dim]Cached. Use --refresh to re-fetch.[/]")


def refs(
    niche: str = typer.Option(..., "--niche", "-n"),
    limit: int = typer.Option(20, "--limit"),
) -> None:
    """List cached reference outliers for a niche."""
    result = scrape_niche(niche)  # returns from cache if fresh
    for o in result["outliers"][:limit]:
        title = o.get("snippet", {}).get("title", "")
        score = o.get("outlier_score", 0)
        path = o.get("thumbnail_path", "")
        console.print(f"[green]{score}x[/] [cyan]{o.get('channel_name')}[/] — {title}")
        if path:
            console.print(f"  [dim]{path}[/]")


def analyze(
    paths: list[Path] = typer.Argument(..., help="One or more image paths to analyze"),
    niche: str = typer.Option("general", "--niche", "-n"),
    output: Path = typer.Option(None, "--output", "-o", help="Save brief to file"),
) -> None:
    """Run Gemini Vision style brief on arbitrary thumbnails."""
    console.print(f"[bold]Analyzing {len(paths)} thumbnails...[/]")
    brief = analyze_thumbnails(list(paths), niche)
    console.print("\n[bold]STYLE BRIEF:[/]\n")
    console.print(brief)
    if output:
        output.write_text(brief, encoding="utf-8")
        console.print(f"\n[green]✓[/] Saved to {output}")


def brief(
    niche: str = typer.Option(..., "--niche", "-n"),
    refresh: bool = typer.Option(False, "--refresh"),
) -> None:
    """Get or build the cached style brief for a niche."""
    text = get_or_build_style_brief(niche, refresh=refresh)
    console.print(f"\n[bold]STYLE BRIEF — {niche}[/]\n")
    console.print(text)


def registry() -> None:
    """List all niches and channels in the registry."""
    reg = load_registry()
    for niche_name, body in reg.items():
        console.print(f"\n[bold cyan]{niche_name}[/]")
        for ch in body.get("channels", []):
            tags = ", ".join(ch.get("style_tags", []))
            console.print(f"  • {ch['name']:<30} [dim]{ch['channel_id']}[/]  [yellow]{tags}[/]")
    console.print(f"\n[green]✓[/] {len(reg)} niches, "
                  f"{sum(len(v.get('channels', [])) for v in reg.values())} total channels")


def niches() -> None:
    """List available niche keys."""
    for n in list_niches():
        console.print(f"  • {n}")
