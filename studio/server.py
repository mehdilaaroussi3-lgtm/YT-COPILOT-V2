"""YTcopilot Studio — FastAPI shell.

Mounts static files + every router. All business logic lives in core/, generators/,
scraper/, agents/ — this file only wires HTTP to Python functions.
"""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from core.pairing_validator import validate_pairing
from core.profile_loader import list_profiles
from core.text_extractor import extract_hook, suggest_alternatives
from scraper.registry_manager import list_niches
from studio.routers import bookmarks, ideas, outliers, settings, style_channels, thumbnails, titles, trackers, winners
from studio.routers.common import CACHE_DIR, OUTPUT_DIR

STATIC_DIR = Path(__file__).resolve().parent / "static"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="YTcopilot Studio", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/output", StaticFiles(directory=OUTPUT_DIR), name="output")
if CACHE_DIR.exists():
    app.mount("/cache", StaticFiles(directory=CACHE_DIR), name="cache")

# --- Routers ---
app.include_router(outliers.router)
app.include_router(trackers.router)
app.include_router(bookmarks.router)
app.include_router(ideas.router)
app.include_router(titles.router)
app.include_router(thumbnails.router)
app.include_router(winners.router)
app.include_router(settings.router)
app.include_router(style_channels.router)


# --- Top-level endpoints ---
@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    return HTMLResponse((STATIC_DIR / "index.html").read_text(encoding="utf-8"))


@app.get("/api/health")
async def health() -> dict:
    return {"ok": True, "version": "0.2.0"}


@app.get("/api/channels")
async def channels() -> dict:
    return {"channels": list_profiles()}


@app.get("/api/niches")
async def niches() -> dict:
    return {"niches": list_niches()}


@app.get("/api/hook")
async def hook(title: str, channel: str | None = None) -> dict:
    """Preview the hook that will be rendered on the thumbnail.

    If `channel` is a channel ID we already have a cached text DNA for,
    returns the smart channel-native hook. Otherwise falls back to the
    regex-based keyword extraction. Never triggers a channel scan — this
    endpoint must stay fast for live typing.
    """
    smart_h = ""
    used_dna = False
    if channel and channel.startswith("UC"):
        try:
            from data.db import db
            d = db()
            row = d["channel_briefs"].get(channel) if "channel_briefs" in d.table_names() else None
            text_dna = (row or {}).get("text_dna") or ""
            if text_dna:
                from core.channel_text_dna import generate_smart_hook
                smart_h = generate_smart_hook(title, text_dna)
                used_dna = bool(smart_h)
        except Exception:  # noqa: BLE001
            smart_h = ""

    h = smart_h or extract_hook(title)
    return {
        "hook": h,
        "smart": used_dna,
        "alternatives": suggest_alternatives(title),
        "pairing": asdict(validate_pairing(title, h)),
    }


def start_studio(host: str = "127.0.0.1", port: int = 8000) -> None:
    import uvicorn
    print(f"\n  YTcopilot Studio → http://{host}:{port}\n")
    uvicorn.run(app, host=host, port=port, log_level="info")
