"""Agent CLI commands: discover, explore, trends, similar, patterns, research."""
from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

console = Console()


def discover(
    keyword: str = typer.Argument(..., help="Niche keyword to discover outliers in."),
    max_channels: int = typer.Option(15, "--max-channels"),
    min_score: float = typer.Option(5.0, "--min-score"),
) -> None:
    """Find 5x+ outlier videos for a keyword across YouTube."""
    from agents.outlier_discovery import OutlierDiscoveryAgent
    agent = OutlierDiscoveryAgent()
    console.print(f"[cyan]Discovering outliers for:[/] {keyword}")
    result = agent.discover_niche(keyword, max_channels=max_channels, min_score=min_score)
    console.print(f"\n[green]✓[/] Scanned {result['channels_scanned']} channels, "
                  f"found {result['outliers_found']} outliers")

    table = Table(title="Top outliers")
    table.add_column("Score", justify="right", style="green")
    table.add_column("Views", justify="right")
    table.add_column("Title", overflow="fold")
    for o in result["top_outliers"][:20]:
        table.add_row(f"{o['outlier_score']}x",
                      f"{int(o['statistics'].get('viewCount', 0)):,}",
                      o["snippet"]["title"][:80])
    console.print(table)


def explore(
    keyword: str = typer.Argument(...),
    max_channels: int = typer.Option(25, "--max-channels"),
) -> None:
    """Map the channel landscape for a topic."""
    from agents.niche_explorer import NicheExplorerAgent
    agent = NicheExplorerAgent()
    channels = agent.explore(keyword, max_channels=max_channels)
    table = Table(title=f"Channels for '{keyword}'")
    table.add_column("Channel", style="cyan")
    table.add_column("Subs", justify="right", style="green")
    table.add_column("Videos", justify="right")
    table.add_column("Total Views", justify="right")
    for c in channels[:25]:
        table.add_row(c["name"], f"{c['subs']:,}", f"{c['videos']:,}",
                      f"{c['views']:,}")
    console.print(table)


def trends(
    niche: str = typer.Option(..., "--niche", "-n"),
    recent: int = typer.Option(14, "--recent-days"),
    baseline: int = typer.Option(60, "--baseline-days"),
) -> None:
    """Detect rising vs falling thumbnail style tags."""
    from agents.trend_detector import TrendDetectorAgent
    agent = TrendDetectorAgent()
    result = agent.detect(niche, recent_days=recent, baseline_days=baseline)
    table = Table(title=f"Trend report — {niche}")
    table.add_column("Tag")
    table.add_column("Recent", justify="right")
    table.add_column("Baseline", justify="right")
    table.add_column("Direction", style="bold")
    for r in result["report"][:30]:
        color = {"rising": "green", "falling": "red", "flat": "dim"}[r["direction"]]
        table.add_row(r["tag"], str(r["recent"]), str(r["baseline"]),
                      f"[{color}]{r['direction']}[/]")
    console.print(table)


def similar(
    image: Path = typer.Argument(..., exists=True),
    limit: int = typer.Option(10, "--limit"),
) -> None:
    """Describe an image then find similar cached thumbnails by tag overlap."""
    from agents.thumbnail_style import ThumbnailStyleAgent
    agent = ThumbnailStyleAgent()
    desc = agent.describe(image)
    if not desc:
        console.print("[red]Vision description failed.[/]")
        return
    console.print(f"[cyan]Description:[/] {desc.get('subject')}")
    console.print(f"[cyan]Tags:[/] {', '.join(desc.get('style_tags', []))}")
    matches = agent.find_similar(desc.get("style_tags", []), limit=limit)
    if not matches:
        console.print("\n[yellow]No similar thumbnails in cache yet.[/] "
                      "Run `thumbcraft index --niche X` first.")
        return
    table = Table(title="Similar")
    table.add_column("Video"); table.add_column("Subject"); table.add_column("Tags")
    for m in matches:
        table.add_row(m["video_id"], (m.get("description") or "")[:50],
                      m.get("style_tags", ""))
    console.print(table)


def patterns(
    niche: str = typer.Option(..., "--niche", "-n"),
    min_score: float = typer.Option(5.0, "--min-score"),
) -> None:
    """Extract recurring title formulas from outlier videos in DB."""
    from agents.title_pattern import TitlePatternAgent
    agent = TitlePatternAgent()
    pats = agent.extract_patterns(niche, min_outlier_score=min_score)
    if not pats:
        console.print("[yellow]No patterns extracted.[/] "
                      "Run `thumbcraft discover <keyword>` first to populate the DB.")
        return
    for p in pats:
        console.print(f"\n[bold cyan]{p['pattern']}[/] [dim](×{p['frequency']})[/]")
        for ex in p.get("examples", [])[:3]:
            console.print(f"  • {ex}")


def research_update() -> None:
    """Pull latest 1of10 blog posts into the DB."""
    from agents.research_scraper import ResearchScraperAgent
    agent = ResearchScraperAgent()
    result = agent.update()
    console.print(f"[green]✓[/] Imported {result['new_articles']} new articles")
    for r in agent.list_recent(10):
        console.print(f"  [cyan]{r['title']}[/]\n    [dim]{r['url']}[/]")


def index(
    niche: str = typer.Option(..., "--niche", "-n", help="Niche key to index thumbnails for"),
    limit: int = typer.Option(20, "--limit"),
) -> None:
    """Run Vision describe over cached thumbnails for a niche, populating the style index."""
    from agents.thumbnail_style import ThumbnailStyleAgent
    from data.db import db
    agent = ThumbnailStyleAgent()
    d = db()
    rows = list(d["thumbnails"].rows_where(
        "description IS NULL OR description = ''", limit=limit,
    ))
    if not rows:
        console.print("[yellow]No un-indexed thumbnails. Run `thumbcraft discover` first.[/]")
        return
    for r in rows:
        path = Path(r["file_path"])
        if not path.exists():
            continue
        console.print(f"  Indexing {r['video_id']}...")
        desc = agent.index_video(r["video_id"], path)
        if desc:
            console.print(f"    [green]→[/] {', '.join(desc.get('style_tags', [])[:5])}")
