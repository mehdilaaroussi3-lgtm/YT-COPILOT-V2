"""/api/outliers — random, search, detail, scan, smart-search."""
from __future__ import annotations

import asyncio
import json
import re
from fastapi import APIRouter

from core.outliers import get_outlier, random_outliers, search_by_channels, search_outliers
from studio.routers.common import to_cache_url

router = APIRouter(prefix="/api/outliers")

# Job store for scan progress SSE
_scan_job: dict = {"status": "idle", "events": [], "result": None}


def _decorate(items: list[dict]) -> list[dict]:
    for it in items:
        # Prefer locally-cached file; fall back to YouTube CDN (free, always works)
        local_url = to_cache_url(it.get("thumbnail_path"))
        it["thumb_url"] = local_url or it.get("yt_thumb_url") or ""
    return items


@router.get("/random")
def random(limit: int = 12, min_score: float = 2.0) -> dict:
    return {"items": _decorate(random_outliers(limit=limit, min_score=min_score))}


@router.get("/search")
def search(q: str = "", niche: str | None = None,
            channel_id: str | None = None, limit: int = 60) -> dict:
    return {"items": _decorate(search_outliers(q, niche, channel_id, limit))}


@router.post("/scan")
async def trigger_scan(force: bool = False) -> dict:
    """Kick off a full background scan of all seed + tracked channels."""
    _scan_job.update({"status": "running", "events": [], "result": None})

    def on_progress(msg: str) -> None:
        _scan_job["events"].append(msg)

    def _run() -> None:
        from core.weekly_scan import scan_all_channels
        result = scan_all_channels(force=force, on_progress=on_progress)
        _scan_job.update({"status": "done", "result": result})

    loop = asyncio.get_running_loop()
    loop.run_in_executor(None, _run)
    return {"ok": True, "message": "Scan started"}


@router.get("/scan/status")
def scan_status() -> dict:
    return _scan_job


@router.post("/enrich")
async def trigger_enrich(force: bool = False) -> dict:
    """Resolve all curated handles → write to registry → scan all channels."""
    _scan_job.update({"status": "running", "events": [], "result": None})

    def on_progress(msg: str) -> None:
        _scan_job["events"].append(msg)

    def _run() -> None:
        from core.registry_seeder import seed_registry
        from core.weekly_scan import scan_all_channels
        on_progress("Resolving channel handles via YouTube API…")
        seed_result = seed_registry(force=force, on_progress=on_progress)
        on_progress(
            f"Seeded {seed_result['resolved']} new channels "
            f"({seed_result['skipped']} already present, "
            f"{len(seed_result['failed'])} failed)"
        )
        scan_result = scan_all_channels(force=True, on_progress=on_progress)
        _scan_job.update({"status": "done", "result": {**seed_result, **scan_result}})

    asyncio.get_running_loop().run_in_executor(None, _run)
    return {"ok": True, "message": "Enrichment started — poll /api/outliers/scan/status"}


@router.get("/smart-finds")
def list_smart_finds() -> dict:
    """Return all saved Smart Find searches, newest first."""
    from data.db import db as _db
    d = _db()
    if "smart_finds" not in d.table_names():
        return {"items": []}
    rows = list(d["smart_finds"].rows_where(order_by="rowid desc", limit=50))
    for r in rows:
        r["channel_ids"] = json.loads(r.get("channel_ids") or "[]")
        r["channel_names"] = json.loads(r.get("channel_names") or "[]")
    return {"items": rows}


@router.get("/by-channels")
def by_channels(ids: str = "", limit: int = 200) -> dict:
    """Return outliers for a comma-separated list of channel IDs."""
    channel_ids = [c.strip() for c in ids.split(",") if c.strip()]
    return {"items": _decorate(search_by_channels(channel_ids, limit=limit))}


@router.post("/smart-search")
async def smart_search(body: dict) -> dict:
    """Describe a style → LLM generates search queries → YouTube finds real channels → scan."""
    description = (body.get("description") or "").strip()
    if not description:
        return {"error": "description is required"}

    _scan_job.update({"status": "running", "events": [], "result": None})

    def on_progress(msg: str) -> None:
        _scan_job["events"].append(msg)

    def _run() -> None:
        import datetime as dt
        import httpx
        from agents.outlier_discovery import OutlierDiscoveryAgent
        from generators.gemini_text import generate_text
        from scraper.youtube_scraper import API_BASE, ReferenceScraper

        # ── Step 1: LLM generates targeted YouTube search queries ────────────
        on_progress("Generating targeted search queries…")
        # Prompt is deliberately terse and output-first so the model can't
        # drift into prose. The task is ONLY to produce search query strings.
        prompt = (
            "Task: produce 5 YouTube search query strings for the YouTube search API.\n\n"
            f'Style description to match: "{description}"\n\n'
            "Query requirements:\n"
            "- Target long-form channels (10+ min videos) with premium thumbnail design\n"
            "- Be specific about visual style and niche (not just the topic)\n"
            "- No brand/channel names in the queries — use descriptive style terms\n"
            "- Example good queries: \"cinematic faceless documentary channel\", "
            "\"dark moody explainer high production value\", "
            "\"illustrated animated science education youtube\"\n\n"
            "Output format — ONLY this JSON array, nothing else, no explanation:\n"
            '["query 1", "query 2", "query 3", "query 4", "query 5"]'
        )
        try:
            raw = generate_text(prompt)
        except Exception as e:  # noqa: BLE001
            _scan_job.update({"status": "done", "result": {"error": f"LLM error: {e}"}})
            return

        # Try strict JSON array match first, then fall back to quoted-string extraction
        queries: list[str] = []
        match = re.search(r"\[.*?\]", raw, re.DOTALL)
        if match:
            try:
                queries = [q for q in json.loads(match.group()) if isinstance(q, str)]
            except json.JSONDecodeError:
                pass
        if not queries:
            # Fallback: pull any "quoted strings" from the response
            queries = re.findall(r'"([^"]{10,120})"', raw)
        if not queries:
            _scan_job.update({"status": "done", "result": {"error": f"Could not extract search queries from LLM response. Raw: {raw[:300]}"}})
            return

        on_progress(f"Searching YouTube with {len(queries)} queries…")

        # ── Step 2: YouTube search.list → candidate channel IDs ─────────────
        scraper = ReferenceScraper.from_config()
        seen: set[str] = set()
        candidates: list[dict] = []

        for query in queries[:5]:
            on_progress(f"  🔍 {query}")
            try:
                resp = httpx.get(f"{API_BASE}/search", params={
                    "part": "snippet",
                    "q": query,
                    "type": "channel",
                    "maxResults": 10,
                    "key": scraper.api_key,
                }, timeout=20.0)
                resp.raise_for_status()
                for it in resp.json().get("items", []):
                    sn = it.get("snippet", {})
                    cid = sn.get("channelId") or (it.get("id") or {}).get("channelId", "")
                    name = sn.get("channelTitle") or sn.get("title", "")
                    if cid and cid not in seen:
                        seen.add(cid)
                        candidates.append({"channel_id": cid, "title": name})
            except Exception as e:  # noqa: BLE001
                on_progress(f"  [search error] {e}")

        if not candidates:
            _scan_job.update({"status": "done", "result": {"error": "YouTube search returned no channels. Check API key quota."}})
            return

        # ── Step 3: Filter by subscriber count — premium channels only ───────
        # Require 100k+ subscribers so we're learning from established creators
        MIN_SUBS = 100_000
        on_progress(f"Filtering {len(candidates)} candidates by quality (≥{MIN_SUBS//1000}k subs)…")
        try:
            all_cids = [c["channel_id"] for c in candidates]
            ch_stats = scraper.get_channel_stats(all_cids)
            channels: list[dict] = []
            for c in candidates:
                stats = ch_stats.get(c["channel_id"], {})
                subs = stats.get("subscriber_count", 0)
                if subs >= MIN_SUBS:
                    channels.append(c)
                else:
                    on_progress(f"  skipped {c['title']} ({subs:,} subs — below threshold)")
        except Exception as e:  # noqa: BLE001
            on_progress(f"  [subscriber filter error] {e} — using all candidates")
            channels = candidates

        if not channels:
            _scan_job.update({"status": "done", "result": {"error": f"No channels passed the {MIN_SUBS//1000}k subscriber threshold."}})
            return

        on_progress(f"{len(channels)} premium channels qualified — scanning for top thumbnails…")

        # ── Step 4: Scan each channel — long-form outliers only ──────────────
        agent = OutlierDiscoveryAgent()
        # 3.5x outlier score — only genuinely over-performing thumbnails
        MIN_SCORE = 3.5
        total_outliers = 0
        scanned: list[dict] = []

        for ch in channels:
            on_progress(f"  scanning {ch['title']}…")
            try:
                outliers = agent.scan_channel(
                    ch["channel_id"], ch["title"],
                    min_score=MIN_SCORE, download=True,
                )
                total_outliers += len(outliers)
                scanned.append(ch)
                on_progress(f"    → {len(outliers)} outliers")
            except Exception as e:  # noqa: BLE001
                on_progress(f"    [error] {e}")

        channel_ids = [ch["channel_id"] for ch in scanned]
        channel_names = [ch["title"] for ch in scanned]
        result = {
            "source": "smart_search",
            "description": description,
            "channel_ids": channel_ids,
            "channel_names": channel_names,
            "channels_scanned": len(scanned),
            "total_outliers": total_outliers,
        }

        # ── Persist to smart_finds table ─────────────────────────────────────
        try:
            from data.db import db as _db
            _db()["smart_finds"].insert({
                "description": description,
                "channel_ids": json.dumps(channel_ids),
                "channel_names": json.dumps(channel_names),
                "channels_scanned": len(scanned),
                "total_outliers": total_outliers,
                "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            }, alter=True)
        except Exception as _e:  # noqa: BLE001
            print(f"[smart-find] persist failed: {_e}")

        _scan_job.update({"status": "done", "result": result})

    asyncio.get_running_loop().run_in_executor(None, _run)
    return {"ok": True, "message": "Smart search started — poll /api/outliers/scan/status"}


# ── New endpoints added in rework ──────────────────────────────────────────────

@router.get("/recent")
def recent(limit: int = 6, min_score: float = 2.0) -> dict:
    """Most-recently-indexed outliers by fetched_at DESC. Used by Home page."""
    from core.outliers import recent_outliers
    return {"items": _decorate(recent_outliers(limit=limit, min_score=min_score))}


@router.get("/premium")
def premium(limit: int = 10, min_subs: int = 100_000,
             min_score: float = 3.0, max_score: float = 25.0,
             faceless: int = 1) -> dict:
    """Premium-channel-only outliers, score-capped. Used by Home showcase.

    faceless=1 → prioritise illustrated/text-heavy niches (history, finance, ai, etc).
    """
    from core.outliers import premium_outliers
    return {"items": _decorate(premium_outliers(
        limit=limit, min_subs=min_subs, min_score=min_score,
        max_score=max_score, faceless_bias=bool(faceless),
    ))}


@router.get("/stats")
def stats() -> dict:
    """Score-tier counts for the Dashboard (2x / 3x / 5x / 10x buckets)."""
    from core.outliers import outlier_stats
    return outlier_stats()


@router.get("/niche-stats")
def get_niche_stats() -> dict:
    """Per-niche breakdown: channels, videos, avg score, last scanned."""
    from core.outliers import niche_stats
    return {"items": niche_stats()}


@router.get("/style-tags")
def get_style_tags(top_n: int = 15) -> dict:
    """Top N style tags across all indexed thumbnails (for Dashboard tag cloud)."""
    from core.outliers import style_tags_summary
    return {"tags": style_tags_summary(top_n=top_n)}


@router.get("/niches")
def get_niches() -> dict:
    """Distinct niche values for filter dropdowns."""
    from core.outliers import available_niches
    return {"niches": available_niches()}


@router.get("/channels-random")
def channels_random(limit: int = 30, niche: str | None = None) -> dict:
    """Shuffled mix of curated + tracked channels with outlier stats and mini-thumb IDs."""
    from core.outliers import random_channels
    from studio.routers.common import to_cache_url
    items = random_channels(limit=limit, niche=niche)
    # Resolve thumb_urls for the top_video_ids mini-strip
    for ch in items:
        ch["top_thumb_urls"] = [
            f"https://img.youtube.com/vi/{vid}/hqdefault.jpg"
            for vid in ch.get("top_video_ids", [])
        ]
    return {"items": items}


@router.get("/{video_id}")
def detail(video_id: str) -> dict:
    item = get_outlier(video_id)
    if not item:
        return {"error": "not found"}
    local_url = to_cache_url(item.get("thumbnail_path"))
    item["thumb_url"] = local_url or item.get("yt_thumb_url") or ""
    return item
