"""YTcopilot CLI entry point."""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure repo root (which contains `data/`, `channels/`, etc.) is importable
# even when launched via the thumbcraft.exe wrapper from another cwd.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Force UTF-8 stdout/stderr on Windows so rich glyphs (✓, ✗, →) don't crash.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass

import typer
from rich.console import Console

from cli.commands import agents as agents_cmd
from cli.commands import generate as generate_cmd
from cli.commands import produce as produce_cmd
from cli.commands import reverse as reverse_cmd
from cli.commands import scrape as scrape_cmd
from cli.commands import studio as studio_cmd

app = typer.Typer(
    name="thumbcraft",
    help="Production-grade YouTube thumbnail generator powered by YTC 3.0 Pro Image.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()

app.command("generate", help="Generate thumbnails from a video title.")(generate_cmd.generate)
app.command("scrape", help="Scrape outlier thumbnails for a niche.")(scrape_cmd.scrape)
app.command("refs", help="List cached reference thumbnails for a niche.")(scrape_cmd.refs)
app.command("analyze", help="Run Gemini Vision style brief on thumbnails.")(scrape_cmd.analyze)
app.command("brief", help="Get or build the style brief for a niche.")(scrape_cmd.brief)
app.command("registry", help="List all channels in the registry.")(scrape_cmd.registry)
app.command("niches", help="List available niche keys.")(scrape_cmd.niches)

# Phase 3 agents
app.command("discover", help="Find 5x+ outlier videos for a keyword.")(agents_cmd.discover)
app.command("explore", help="Map channels in a topic landscape.")(agents_cmd.explore)
app.command("trends", help="Detect rising/falling thumbnail style tags.")(agents_cmd.trends)
app.command("similar", help="Find cached thumbnails similar to an image.")(agents_cmd.similar)
app.command("patterns", help="Extract recurring title formulas.")(agents_cmd.patterns)
app.command("index", help="Run Vision describe over cached thumbnails.")(agents_cmd.index)
app.command("research-update", help="Pull latest 1of10 blog posts.")(agents_cmd.research_update)

# Studio + refine + profile
app.command("studio", help="Launch local web UI at http://127.0.0.1:8000")(studio_cmd.studio)
app.command("refine", help="Refine an existing thumbnail with natural language.")(studio_cmd.refine)
app.command("profiles", help="List channel profiles.")(studio_cmd.profile_list)

# Ultimate Reverse Engineer
app.command("reverse", help="Reverse-engineer a YouTube video into a production blueprint.")(reverse_cmd.reverse)

# Production Pipeline
app.command("produce", help="Produce a video in the style of a reversed blueprint.")(produce_cmd.produce)


@app.command("version")
def version() -> None:
    """Print YTcopilot version."""
    console.print("[bold cyan]YTcopilot[/] v0.1.0  (Phase 1 — Foundation)")


if __name__ == "__main__":
    app()
