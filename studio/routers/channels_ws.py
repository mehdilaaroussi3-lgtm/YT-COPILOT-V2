"""My Channels workspace API.

Manages the user's own channels (brand identities with a locked production
formula copied from a reference YouTube channel). Isolated from the existing
/api/trackers (tracked competitor channels) and /api/channels (profile list).
"""
from __future__ import annotations

import datetime as dt
import random
import string
import threading

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from data.db import db
from core.reverse.pipeline import reverse as ure_reverse
from core.channel_dna_synth import synthesize as dna_synthesize, DNA_DIR

router = APIRouter(prefix="/api/my-channels", tags=["my-channels"])

# In-memory job tracking
_scan_cancel: set[str] = set()         # channel names requested to abort
_scan_jobs: dict[str, dict] = {}       # keyed by channel name
_produce_jobs: dict[str, dict] = {}    # keyed by str(video_id)  [legacy full-pipeline]
_logo_jobs: dict[str, dict] = {}       # keyed by channel name
_idea_jobs: dict[str, dict] = {}       # keyed by job_id
_thumbnail_jobs: dict[str, dict] = {}  # keyed by str(video_id)
_script_jobs: dict[str, dict] = {}     # keyed by str(video_id)
_section_jobs: dict[str, dict] = {}    # keyed by f"{video_id}:{sid}"
_final_jobs: dict[str, dict] = {}      # keyed by str(video_id)

# ── Pydantic models ──────────────────────────────────────────────────────────

class ChannelCreate(BaseModel):
    name: str
    niche: str
    reference_channel_id: str = ""
    reference_channel_name: str = ""
    reference_yt_url: str = ""
    avatar_color: str = ""
    target_audience: str = ""
    tone: str = ""
    voice_id: str = ""
    default_duration: str = "10min"


class ChannelUpdate(BaseModel):
    niche: str | None = None
    reference_channel_id: str | None = None
    reference_yt_url: str | None = None
    reference_channel_name: str | None = None
    target_audience: str | None = None
    tone: str | None = None
    voice_id: str | None = None
    default_duration: str | None = None


class VideoCreate(BaseModel):
    topic: str
    brief: str = ""
    duration_hint: str = "10min"
    resolution: str = "4K"
    status: str = "titled"


class VideoUpdate(BaseModel):
    status: str | None = None
    brief: str | None = None
    thumbnail_path: str | None = None
    script_json: str | None = None
    script_status: str | None = None
    blueprint_path: str | None = None
    production_name: str | None = None
    final_mp4_path: str | None = None


class ProduceRequest(BaseModel):
    resolution: str = "4K"
    duration_hint: str = "10min"
    voice_id: str = ""


class ScriptRequest(BaseModel):
    duration_hint: str = "10min"


class ScriptSave(BaseModel):
    script_json: str


# ── Helpers ──────────────────────────────────────────────────────────────────


def _get_channel_video_urls(handle: str, channel_id: str, n: int = 10) -> list[str]:
    """Return top N video URLs for a channel, best-first.

    Priority:
    1. DB outlier index (sorted by outlier_score desc) — these ARE the top
       performers we've already measured.
    2. yt-dlp most-viewed playlist — when the channel isn't in our DB yet.
    """
    # Priority 1 — already-scored videos in our DB (best by outlier score)
    if channel_id:
        try:
            _d = db()
            if "videos" in _d.table_names():
                rows = list(_d["videos"].rows_where(
                    "channel_id = ?", [channel_id],
                    order_by="outlier_score desc",
                    limit=n,
                ))
                urls = [f"https://www.youtube.com/watch?v={r['video_id']}"
                        for r in rows if r.get("video_id")]
                if len(urls) >= n:
                    return urls
        except Exception:
            pass

    # Priority 2 — yt-dlp, sorted by view count (most popular = best)
    import yt_dlp
    urls_to_try = []
    if handle:
        urls_to_try.append(f"https://www.youtube.com/@{handle}/videos")
    if channel_id:
        urls_to_try.append(f"https://www.youtube.com/channel/{channel_id}/videos")

    for url in urls_to_try:
        try:
            opts = {
                "quiet": True,
                "no_warnings": True,
                "extract_flat": "in_playlist",
                "playlist_items": f"1-50",          # fetch 50, pick top-N by view_count
                "playlistsort": "viewcount",         # most viewed first
            }
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                entries = (info or {}).get("entries") or []
                # Sort by view_count descending if available
                entries.sort(key=lambda e: int(e.get("view_count") or 0), reverse=True)
                result = [f"https://www.youtube.com/watch?v={e['id']}"
                          for e in entries if e.get("id")]
                if result:
                    return result[:n]
        except Exception:
            continue
    return []

_COLORS = [
    "#6366f1", "#8b5cf6", "#ec4899", "#f59e0b",
    "#10b981", "#3b82f6", "#ef4444", "#14b8a6",
]

def _rand_color() -> str:
    return random.choice(_COLORS)


def _channel_row(row: dict) -> dict:
    d = db()
    video_count = 0
    if "channel_videos" in d.table_names():
        video_count = next(
            d.execute(
                "SELECT COUNT(*) FROM channel_videos WHERE channel_name = ?",
                [row["name"]],
            )
        )[0]
    return {**row, "video_count": video_count}


# ── Channels CRUD ────────────────────────────────────────────────────────────

@router.get("")
async def list_channels():
    d = db()
    if "my_channels" not in d.table_names():
        return {"items": []}
    rows = list(d["my_channels"].rows_where(order_by="created_at DESC"))
    return {"items": [_channel_row(r) for r in rows]}


@router.post("")
async def create_channel(body: ChannelCreate):
    d = db()
    if "my_channels" in d.table_names():
        existing = list(d["my_channels"].rows_where("name = ?", [body.name]))
        if existing:
            raise HTTPException(400, f"Channel '{body.name}' already exists.")
    row = {
        "name": body.name.strip(),
        "niche": body.niche.strip(),
        "reference_channel_id": body.reference_channel_id.strip(),
        "reference_channel_name": body.reference_channel_name.strip(),
        "reference_yt_url": body.reference_yt_url.strip(),
        "dna_path": "",
        "logo_path": "",
        "avatar_color": body.avatar_color or _rand_color(),
        "target_audience": body.target_audience.strip(),
        "tone": body.tone.strip(),
        "voice_id": body.voice_id.strip(),
        "default_duration": body.default_duration.strip() or "10min",
        "created_at": dt.datetime.now(dt.UTC).isoformat(),
    }
    d["my_channels"].insert(row, alter=True)

    # Auto-generate logo in background
    _start_logo_job(body.name.strip(), body.niche.strip(),
                    body.reference_channel_name.strip(),
                    body.reference_channel_id.strip())

    return _channel_row(row)


@router.get("/{name}")
async def get_channel(name: str):
    d = db()
    rows = list(d["my_channels"].rows_where("name = ?", [name]))
    if not rows:
        raise HTTPException(404, "Channel not found.")
    return _channel_row(rows[0])


@router.patch("/{name}")
async def update_channel(name: str, body: ChannelUpdate):
    d = db()
    rows = list(d["my_channels"].rows_where("name = ?", [name]))
    if not rows:
        raise HTTPException(404, "Channel not found.")
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if updates:
        d["my_channels"].update(name, updates)
    return _channel_row(list(d["my_channels"].rows_where("name = ?", [name]))[0])


@router.delete("/{name}")
async def delete_channel(name: str):
    d = db()
    # Archive logo before deletion so it's never lost
    try:
        from core.logo_gen import archive_existing_logo
        archive_existing_logo(name)
    except Exception:
        pass
    if "my_channels" in d.table_names():
        d.execute("DELETE FROM my_channels WHERE name = ?", [name])
        d.conn.commit()
    if "channel_videos" in d.table_names():
        d.execute("DELETE FROM channel_videos WHERE channel_name = ?", [name])
        d.conn.commit()
    return {"ok": True}


# ── Videos CRUD ──────────────────────────────────────────────────────────────

@router.get("/{name}/videos")
async def list_videos(name: str):
    d = db()
    if "channel_videos" not in d.table_names():
        return {"items": []}
    rows = list(
        d["channel_videos"].rows_where(
            "channel_name = ?", [name], order_by="created_at DESC"
        )
    )
    return {"items": rows}


@router.post("/{name}/videos")
async def create_video(name: str, body: VideoCreate):
    d = db()
    channels = list(d["my_channels"].rows_where("name = ?", [name]))
    if not channels:
        raise HTTPException(404, "Channel not found.")
    row = {
        "channel_name": name,
        "topic": body.topic.strip(),
        "status": body.status,
        "blueprint_path": "",
        "production_name": "",
        "final_mp4_path": "",
        "duration_hint": body.duration_hint,
        "resolution": body.resolution,
        "created_at": dt.datetime.now(dt.UTC).isoformat(),
    }
    d["channel_videos"].insert(row)
    inserted = list(
        d["channel_videos"].rows_where(
            "channel_name = ? AND topic = ?",
            [name, body.topic],
            order_by="created_at DESC",
        )
    )[0]
    return inserted


@router.patch("/{name}/videos/{video_id}")
async def update_video(name: str, video_id: int, body: VideoUpdate):
    d = db()
    rows = list(d["channel_videos"].rows_where("id = ? AND channel_name = ?", [video_id, name]))
    if not rows:
        raise HTTPException(404, "Video not found.")
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if updates:
        d["channel_videos"].update(video_id, updates)
    return list(d["channel_videos"].rows_where("id = ?", [video_id]))[0]


@router.delete("/{name}/videos/{video_id}")
async def delete_video(name: str, video_id: int):
    d = db()
    d["channel_videos"].delete_where("id = ? AND channel_name = ?", [video_id, name])
    return {"ok": True}


# ── Logo generation ──────────────────────────────────────────────────────────

def _start_logo_job(channel_name: str, niche: str, ref_channel_name: str, ref_channel_id: str) -> None:
    """Kick off logo generation in a background thread."""
    if _logo_jobs.get(channel_name, {}).get("status") == "generating":
        return

    _logo_jobs[channel_name] = {"status": "generating", "error": ""}

    def run():
        try:
            # Get avatar URL from tracked channels
            avatar_url = ""
            if ref_channel_id:
                d = db()
                if "tracked_channels" in d.table_names():
                    rows = list(d["tracked_channels"].rows_where("channel_id = ?", [ref_channel_id]))
                    if rows:
                        avatar_url = rows[0].get("avatar_url", "")

            from core.logo_gen import generate_logo
            logo_path = generate_logo(channel_name, niche, ref_channel_name, avatar_url)

            db()["my_channels"].update(channel_name, {"logo_path": str(logo_path)})
            _logo_jobs[channel_name] = {"status": "done", "error": ""}
        except Exception as e:
            _logo_jobs[channel_name] = {"status": "error", "error": str(e)}

    threading.Thread(target=run, daemon=True).start()


@router.post("/{name}/generate-logo")
async def generate_logo_endpoint(name: str):
    d = db()
    rows = list(d["my_channels"].rows_where("name = ?", [name]))
    if not rows:
        raise HTTPException(404, "Channel not found.")
    ch = rows[0]
    _start_logo_job(name, ch.get("niche", ""), ch.get("reference_channel_name", ""), ch.get("reference_channel_id", ""))
    return {"status": "generating"}


@router.get("/{name}/logo-status")
async def logo_status(name: str):
    row = db()["my_channels"].rows_where("name = ?", [name])
    logo_path = (list(row) or [{}])[0].get("logo_path", "")
    job = _logo_jobs.get(name, {"status": "idle" if not logo_path else "done", "error": ""})
    return {**job, "logo_path": logo_path}


# ── DNA scan ─────────────────────────────────────────────────────────────────

@router.post("/{name}/scan")
async def start_scan(name: str, body: dict | None = None):
    """Kick off URE on the top N videos of the reference channel.

    Body: { "num_videos": 1 | 2 | 5 | 10 }  (default 3)
    """
    d = db()
    rows = list(d["my_channels"].rows_where("name = ?", [name]))
    if not rows:
        raise HTTPException(404, "Channel not found.")
    ch = rows[0]
    ref_id = ch.get("reference_channel_id", "")

    # Clamp to allowed values: 1, 2, 5, 10
    raw_n = int((body or {}).get("num_videos", 3))
    num_videos = min([1, 2, 5, 10], key=lambda v: abs(v - raw_n))

    if _scan_jobs.get(name, {}).get("status") == "scanning":
        return {"status": "already_running"}

    _scan_jobs[name] = {
        "status": "scanning", "progress": 0, "total": num_videos,
        "current": "Fetching video list…", "stage": "init",
        "video_idx": 0, "error": "",
    }

    def run():
        try:
            # 1. Get top video URLs (best-first: outlier score → view count)
            handle = ""
            if ref_id and "tracked_channels" in db().table_names():
                tr = list(db()["tracked_channels"].rows_where("channel_id = ?", [ref_id]))
                if tr:
                    handle = tr[0].get("handle", "")

            _scan_jobs[name]["current"] = "Fetching video list…"
            urls = _get_channel_video_urls(handle, ref_id, n=num_videos)
            if not urls:
                _scan_jobs[name] = {"status": "error", "error": "Could not fetch videos from reference channel. Make sure the channel is tracked and has videos.", "progress": 0, "total": 3, "current": "", "stage": "", "video_idx": 0}
                return

            _scan_jobs[name]["total"] = len(urls)
            blueprint_paths = []

            # 2. Run URE on each video — pipe every stage message to the job
            for i, url in enumerate(urls):
                if name in _scan_cancel:
                    _scan_cancel.discard(name)
                    break

                _scan_jobs[name].update({
                    "video_idx": i,
                    "stage": "starting",
                    "current": f"Starting video {i + 1} of {len(urls)}…",
                    "progress": i,
                })

                def _make_progress(vi: int, vt: int):
                    def _p(msg: str) -> None:
                        _scan_jobs[name].update({"current": msg, "stage": msg})
                    return _p

                try:
                    out_dir = ure_reverse(url, progress=_make_progress(i, len(urls)))
                    bp = out_dir / "blueprint.json"
                    if bp.exists():
                        blueprint_paths.append(bp)
                except Exception:
                    pass  # skip failed video, continue with next
                _scan_jobs[name]["progress"] = i + 1

            if not blueprint_paths:
                _scan_jobs[name] = {"status": "error", "error": "All video reverse-engineering attempts failed.", "progress": 0, "total": len(urls), "current": "", "stage": "", "video_idx": 0}
                return

            # 3. Synthesize DNA
            _scan_jobs[name].update({"current": f"Synthesising DNA from {len(blueprint_paths)} video(s)…", "stage": "synthesis"})
            dna_path = dna_synthesize(name, blueprint_paths)

            # 4. Done
            _db = db()
            _db["my_channels"].update(name, {"dna_path": str(dna_path)})
            _db.conn.commit()
            _scan_jobs[name] = {"status": "done", "progress": len(urls), "total": len(urls), "current": f"DNA ready — {len(blueprint_paths)} videos analysed.", "stage": "done", "video_idx": len(urls), "error": ""}

        except Exception as e:
            _scan_jobs[name] = {"status": "error", "error": str(e), "progress": 0, "total": 3, "current": "", "stage": "", "video_idx": 0}

    threading.Thread(target=run, daemon=True).start()
    return {"status": "scanning"}


@router.get("/{name}/scan/status")
async def scan_status(name: str):
    return _scan_jobs.get(name, {"status": "idle", "progress": 0, "total": 3, "current": "", "error": ""})


@router.post("/{name}/scan/abort")
async def scan_abort(name: str):
    """Stop the scan and synthesize DNA from whatever data already exists.

    Priority:
    1. Complete blueprints (blueprint.json) → use directly
    2. Partial URE folders (scenes.json present, no blueprint) → resume URE
       from existing data so frames/scenes aren't re-downloaded
    3. Nothing at all → write a sensible default formula
    """
    from pathlib import Path as _Path
    import json as _json

    _scan_cancel.add(name)

    reverse_dir = _Path("data/reverse")

    # --- Priority 1: complete blueprints ---
    blueprint_paths = sorted(reverse_dir.glob("*/blueprint.json")) if reverse_dir.exists() else []

    # --- Priority 2: partial folders with scenes.json but no blueprint ---
    partial_video_ids = []
    if reverse_dir.exists():
        for vdir in reverse_dir.iterdir():
            if vdir.is_dir() and (vdir / "scenes.json").exists() and not (vdir / "blueprint.json").exists():
                partial_video_ids.append(vdir.name)

    d = db()
    rows = list(d["my_channels"].rows_where("name = ?", [name]))

    if partial_video_ids and not blueprint_paths:
        # Resume URE from existing data — skips download/scene stages automatically
        def resume():
            _scan_jobs[name] = {
                "status": "scanning", "progress": 0, "total": len(partial_video_ids),
                "current": "Resuming from existing scraped data…", "stage": "resuming",
                "video_idx": 0, "error": "",
            }
            bps = []
            for i, vid_id in enumerate(partial_video_ids):
                _scan_jobs[name].update({
                    "video_idx": i, "progress": i,
                    "current": f"Resuming video {i+1}/{len(partial_video_ids)}: {vid_id}…",
                    "stage": "resuming",
                })
                url = f"https://www.youtube.com/watch?v={vid_id}"
                try:
                    def _p(msg: str) -> None:
                        _scan_jobs[name].update({"current": msg, "stage": msg})
                    out_dir = ure_reverse(url, force=False, progress=_p)
                    bp = out_dir / "blueprint.json"
                    if bp.exists():
                        bps.append(bp)
                except Exception as e:
                    pass
                _scan_jobs[name]["progress"] = i + 1

            if bps:
                try:
                    _scan_jobs[name].update({"current": "Synthesising DNA…", "stage": "synthesis"})
                    dna_path = dna_synthesize(name, bps)
                    if rows:
                        d["my_channels"].update(name, {"dna_path": str(dna_path)})
                        d.conn.commit()
                    _scan_jobs[name] = {
                        "status": "done", "progress": len(bps), "total": len(bps),
                        "current": f"DNA built from {len(bps)} resumed video(s).",
                        "stage": "done", "video_idx": len(bps), "error": "",
                    }
                except Exception as e:
                    _scan_jobs[name] = {"status": "error", "error": str(e), "progress": 0, "total": len(partial_video_ids), "current": "", "stage": "", "video_idx": 0}
            else:
                _scan_jobs[name] = {"status": "error", "error": "Resume failed — no blueprints produced.", "progress": 0, "total": len(partial_video_ids), "current": "", "stage": "", "video_idx": 0}

        threading.Thread(target=resume, daemon=True).start()
        return {"ok": True, "mode": "resuming", "videos": partial_video_ids}

    if blueprint_paths:
        try:
            dna_path = dna_synthesize(name, blueprint_paths)
            if rows:
                d["my_channels"].update(name, {"dna_path": str(dna_path)})
                d.conn.commit()
            _scan_jobs[name] = {
                "status": "done", "progress": len(blueprint_paths), "total": len(blueprint_paths),
                "current": f"DNA built from {len(blueprint_paths)} blueprint(s).",
                "stage": "done", "video_idx": len(blueprint_paths), "error": "",
            }
        except Exception as e:
            _scan_jobs[name] = {"status": "error", "error": str(e), "progress": 0, "total": 3, "current": "", "stage": "", "video_idx": 0}
        return {"ok": True, "mode": "blueprints"}

    # --- Priority 3: nothing at all — write sensible defaults ---
    from core.channel_dna_synth import DNA_DIR as _DNA_DIR
    import json as _json
    out_dir = _DNA_DIR / name
    out_dir.mkdir(parents=True, exist_ok=True)
    placeholder = {
        "source": "placeholder",
        "channel_name": name,
        "num_videos": 0,
        "script_formula": {
            "hook_pattern": "knowledge gap — open with a surprising fact or question",
            "arc_beats": [{"beat": "hook"}, {"beat": "setup"}, {"beat": "revelation"}, {"beat": "closer"}],
            "sentence_rhythm": {"avg_words": 12, "stdev": 4},
            "tone": "authoritative, engaging",
            "vo_style": "clear narrator, direct and confident",
        },
        "pacing_template": {"avg_scene_length_s": 5.0, "cuts_per_minute": 12},
        "scene_composition": {"avg_scene_count": 20, "camera_move_distribution": {}, "production_type_distribution": {}},
        "formula_metadata": {},
    }
    dna_path = out_dir / "dna.json"
    dna_path.write_text(_json.dumps(placeholder, indent=2), encoding="utf-8")
    if rows:
        d["my_channels"].update(name, {"dna_path": str(dna_path)})
        d.conn.commit()
    _scan_jobs[name] = {
        "status": "done", "progress": 0, "total": 3,
        "current": "Using default formula — re-scan later for real DNA.", "error": "",
        "stage": "done", "video_idx": 0,
    }
    return {"ok": True, "mode": "placeholder"}


# ── Production ────────────────────────────────────────────────────────────────

@router.post("/{name}/videos/{video_id}/produce")
async def start_produce(name: str, video_id: int, body: ProduceRequest):
    d = db()
    rows = list(d["my_channels"].rows_where("name = ?", [name]))
    if not rows:
        raise HTTPException(404, "Channel not found.")
    ch = rows[0]
    dna_path_str = ch.get("dna_path", "")
    if not dna_path_str:
        raise HTTPException(400, "Channel DNA not built yet. Run a scan first.")

    vrows = list(d["channel_videos"].rows_where("id = ? AND channel_name = ?", [video_id, name]))
    if not vrows:
        raise HTTPException(404, "Video not found.")
    video = vrows[0]

    job_key = str(video_id)
    if _produce_jobs.get(job_key, {}).get("status") == "producing":
        return {"status": "already_running"}

    _produce_jobs[job_key] = {"status": "producing", "current": "Starting production…", "error": "", "output_path": ""}

    def run():
        try:
            from pathlib import Path
            from core.produce.pipeline import produce

            bp = Path(dna_path_str)
            out = produce(
                blueprint_path=bp,
                name=f"{name}-{video_id}",
                topic=video["topic"],
                resolution=body.resolution,
                duration_hint=body.duration_hint,
                voice_id=body.voice_id or None,
                no_gate=True,
                progress=lambda msg: _produce_jobs.__setitem__(job_key, {**_produce_jobs.get(job_key, {}), "current": msg}),
            )
            _produce_jobs[job_key] = {"status": "done", "current": "Production complete.", "error": "", "output_path": str(out)}
            db()["channel_videos"].update(video_id, {"status": "produced", "final_mp4_path": str(out), "production_name": f"{name}-{video_id}"})
        except Exception as e:
            _produce_jobs[job_key] = {"status": "error", "current": "", "error": str(e), "output_path": ""}

    threading.Thread(target=run, daemon=True).start()
    return {"status": "producing"}


@router.get("/{name}/videos/{video_id}/produce/status")
async def produce_status(name: str, video_id: int):
    return _produce_jobs.get(str(video_id), {"status": "idle", "current": "", "error": "", "output_path": ""})


# ── DNA summary ──────────────────────────────────────────────────────────────

@router.get("/{name}/dna-summary")
async def dna_summary(name: str):
    import json
    from pathlib import Path
    d = db()
    rows = list(d["my_channels"].rows_where("name = ?", [name]))
    if not rows:
        raise HTTPException(404, "Channel not found.")
    ch = rows[0]
    if not ch.get("dna_path"):
        raise HTTPException(404, "No DNA yet.")
    try:
        dna = json.loads(Path(ch["dna_path"]).read_text(encoding="utf-8"))
    except Exception as e:
        raise HTTPException(500, f"Could not read DNA file: {e}")

    sf = dna.get("script_formula") or {}
    pt = dna.get("pacing_template") or {}
    arc = sf.get("arc_beats") or []
    rhythm = sf.get("sentence_rhythm") or {}

    return {
        "num_videos":     dna.get("num_videos", 1),
        "hook_pattern":   sf.get("hook_pattern") or "—",
        "tone":           sf.get("tone") or "—",
        "vo_style":       sf.get("vo_style") or "—",
        "avg_words":      rhythm.get("avg_words") if isinstance(rhythm, dict) else 0,
        "arc_beats":      [b.get("beat") or b for b in arc[:6]] if arc else [],
        "avg_scene_s":    round(float(pt.get("avg_scene_length_s") or 0), 1),
        "cuts_per_min":   round(float(pt.get("cuts_per_minute") or 0), 1) if not isinstance(pt.get("cuts_per_minute"), dict) else round(sum(pt["cuts_per_minute"].values()) / max(len(pt["cuts_per_minute"]), 1), 1),
        "scene_count":    pt.get("scene_count") or len(dna.get("scene_prompts") or []) or len(dna.get("scene_composition", {}).get("avg_scene_count") and [] or []),
    }


# ── Ideas generation for a channel ───────────────────────────────────────────

@router.post("/{name}/ideas")
async def generate_channel_ideas(name: str, body: dict = None):
    import uuid, asyncio
    from core import idea_generator

    d = db()
    rows = list(d["my_channels"].rows_where("name = ?", [name]))
    if not rows:
        raise HTTPException(404, "Channel not found.")
    ch = rows[0]

    payload = body or {}
    topic = (payload.get("topic") or "").strip() or None
    count = int(payload.get("count", 6))

    # Build channel context directly — bypass profile_loader entirely so we
    # always have the right niche regardless of whether a profile file exists.
    channel_ctx = {
        "name":                   ch.get("name", name),
        "niche":                  ch.get("niche") or ch.get("target_audience") or "",
        "reference_channel_id":   ch.get("reference_channel_id") or "",
        "reference_channel_name": ch.get("reference_channel_name") or "",
        "tone":                   ch.get("tone") or "",
    }

    job_id = uuid.uuid4().hex[:12]
    _idea_jobs[job_id] = {"status": "running", "items": [], "error": None}

    loop = asyncio.get_event_loop()

    async def _run():
        try:
            items = await loop.run_in_executor(
                None,
                lambda: idea_generator.generate_ideas_for_channel(
                    channel_ctx, topic=topic, count=count
                ),
            )
            if not items:
                _idea_jobs[job_id]["error"] = "LLM returned no ideas — check generate_text logs."
                _idea_jobs[job_id]["status"] = "error"
            else:
                _idea_jobs[job_id]["items"] = items
                _idea_jobs[job_id]["status"] = "done"
        except Exception as e:
            _idea_jobs[job_id]["error"] = str(e)
            _idea_jobs[job_id]["status"] = "error"

    asyncio.create_task(_run())
    return {"job_id": job_id}


@router.get("/{name}/ideas/status/{job_id}")
async def channel_ideas_status(name: str, job_id: str):
    job = _idea_jobs.get(job_id)
    if not job:
        return {"status": "unknown", "items": [], "error": None}
    return job


# ── Title generation for a video ─────────────────────────────────────────────

_title_jobs: dict[str, dict] = {}   # keyed by str(video_id)

@router.post("/{name}/videos/{video_id}/titles")
async def generate_video_titles(name: str, video_id: int):
    """Generate title variants for a video using the same title_generator as
    the main Titles tab — anchored in the reference channel's real past titles."""
    import asyncio
    from core import title_generator

    d = db()
    vrows  = list(d["channel_videos"].rows_where("id = ? AND channel_name = ?", [video_id, name]))
    chrows = list(d["my_channels"].rows_where("name = ?", [name]))
    if not vrows or not chrows:
        raise HTTPException(404, "Video or channel not found.")

    v, ch = vrows[0], chrows[0]
    idea  = v.get("topic") or ""
    # Use the reference channel ID — same anchor the main Titles Generator uses
    ref_ch = ch.get("reference_channel_id") or ch.get("reference_channel_name") or "default"

    job_key = str(video_id)
    _title_jobs[job_key] = {"status": "running", "channel_titles": [], "outlier_titles": [], "error": None}

    loop = asyncio.get_event_loop()
    async def _run():
        try:
            dual = await loop.run_in_executor(
                None, lambda: title_generator.generate_titles_dual(ref_ch, idea, per_source=6)
            )
            _title_jobs[job_key]["channel_titles"] = dual.get("channel_titles", [])
            _title_jobs[job_key]["outlier_titles"]  = dual.get("outlier_titles", [])
            _title_jobs[job_key]["status"] = "done"
        except Exception as e:
            _title_jobs[job_key]["error"]  = str(e)
            _title_jobs[job_key]["status"] = "error"

    asyncio.create_task(_run())
    return {"status": "running"}


@router.get("/{name}/videos/{video_id}/titles/status")
async def video_titles_status(name: str, video_id: int):
    return _title_jobs.get(str(video_id), {"status": "idle", "channel_titles": [], "outlier_titles": [], "error": None})


# ── Thumbnail generation for a video ─────────────────────────────────────────

@router.post("/{name}/videos/{video_id}/thumbnail")
async def start_thumbnail(name: str, video_id: int, body: dict = None):
    """Generate a thumbnail using the reference channel's scraped thumbnails as style refs.
    Optional body: { "style_channel_id": "@handle or channel_id" } to override the style source.
    """
    d = db()
    vrows = list(d["channel_videos"].rows_where("id = ? AND channel_name = ?", [video_id, name]))
    if not vrows:
        raise HTTPException(404, "Video not found.")
    ch_rows = list(d["my_channels"].rows_where("name = ?", [name]))
    if not ch_rows:
        raise HTTPException(404, "Channel not found.")

    job_key = str(video_id)
    if _thumbnail_jobs.get(job_key, {}).get("status") == "generating":
        return {"status": "already_running"}

    _thumbnail_jobs[job_key] = {"status": "generating", "path": "", "url": "", "error": ""}

    v  = vrows[0]
    ch = ch_rows[0]
    style_override = (body or {}).get("style_channel_id", "")

    def run():
        try:
            from pathlib import Path
            from generators.gemini_client import GeminiImageClient
            from core.style_channel import resolve_style_channel
            from core.concept_planner import plan_concepts

            title    = v.get("topic", "")
            niche    = ch.get("niche", "")
            ref_id   = ch.get("reference_channel_id", "")
            ref_url  = ch.get("reference_yt_url", "")
            ref_name = ch.get("reference_channel_name", "")
            audience = ch.get("target_audience", "")
            tone_val = ch.get("tone", "")

            # Resolve reference channel — scrape its real thumbnails as style refs
            # style_override lets the user point at a completely different channel
            channel_ref_key = style_override or ref_id or ref_url or ref_name
            sc = None
            if channel_ref_key:
                try:
                    sc = resolve_style_channel(
                        channel_ref_key,
                        handle_or_url=channel_ref_key if not channel_ref_key.startswith("UC") else None,
                    )
                except Exception:
                    sc = None

            all_refs: list[Path] = list((sc or {}).get("all_reference_paths") or (sc or {}).get("reference_paths") or [])
            style_brief: str = (sc or {}).get("style_brief") or ""
            text_dna: str    = (sc or {}).get("text_dna") or ""
            channel_label    = (sc or {}).get("handle") or ref_name or name

            # Pick one reference thumbnail (spread if regenerating later)
            ref_img: Path | None = all_refs[0] if all_refs else None

            # Generate concept using channel style brief
            concepts = plan_concepts(title, channel_label, style_brief, n=1)
            concept  = concepts[0] if concepts else title

            # Smart hook text from channel's text DNA
            from core.channel_text_dna import generate_smart_hook
            hook = generate_smart_hook(title, text_dna) if text_dna else ""

            tone_hint     = f"tone: {tone_val}" if tone_val else ""
            audience_hint = f"for {audience}" if audience else ""
            text_instruction = (
                f'Include bold text overlay: "{hook}". ' if hook else
                "Bold text overlay on the thumbnail showing the key hook word or phrase. "
            )

            style_hint = f"Style brief: {style_brief[:300]}. " if style_brief else ""
            prompt = (
                f"YouTube thumbnail for: '{title}'. "
                f"Channel niche: {niche}. "
                f"{tone_hint}. {audience_hint}. "
                f"{text_instruction}"
                f"{style_hint}"
                "High contrast, attention-grabbing, professional YouTube thumbnail. "
                "16:9 aspect ratio."
            )

            client = GeminiImageClient.from_config()
            client.aspect_ratio = "16:9"

            refs = [ref_img] if ref_img else []
            result = client.generate(prompt, reference_images=refs)

            out_dir = Path("data/channel_thumbnails") / name
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / f"{video_id}.png"
            out_path.write_bytes(result.data)

            url = f"/channel-thumbnails/{name}/{video_id}.png"
            db()["channel_videos"].update(video_id, {
                "thumbnail_path": str(out_path),
                "status": "thumbnail",
            }, alter=True)
            _thumbnail_jobs[job_key] = {"status": "done", "path": str(out_path), "url": url, "error": ""}
        except Exception as e:
            _thumbnail_jobs[job_key] = {"status": "error", "path": "", "url": "", "error": str(e)}

    threading.Thread(target=run, daemon=True).start()
    return {"status": "generating"}


@router.get("/{name}/videos/{video_id}/thumbnail/status")
async def thumbnail_status(name: str, video_id: int):
    job_key = str(video_id)
    # Check DB for existing thumbnail
    default = {"status": "idle", "path": "", "url": "", "error": ""}
    if job_key not in _thumbnail_jobs:
        d = db()
        if "channel_videos" in d.table_names():
            rows = list(d["channel_videos"].rows_where("id = ?", [video_id]))
            if rows and rows[0].get("thumbnail_path"):
                tp = rows[0]["thumbnail_path"]
                url = f"/channel-thumbnails/{name}/{video_id}.png"
                return {"status": "done", "path": tp, "url": url, "error": ""}
    return _thumbnail_jobs.get(job_key, default)


# ── Script generation ─────────────────────────────────────────────────────────

@router.post("/{name}/videos/{video_id}/script")
async def generate_script(name: str, video_id: int, body: ScriptRequest):
    d = db()
    vrows = list(d["channel_videos"].rows_where("id = ? AND channel_name = ?", [video_id, name]))
    if not vrows:
        raise HTTPException(404, "Video not found.")
    ch_rows = list(d["my_channels"].rows_where("name = ?", [name]))
    if not ch_rows:
        raise HTTPException(404, "Channel not found.")
    ch = ch_rows[0]
    if not ch.get("dna_path"):
        raise HTTPException(400, "Build DNA first.")

    job_key = str(video_id)
    if _script_jobs.get(job_key, {}).get("status") == "generating":
        return {"status": "already_running"}

    _script_jobs[job_key] = {"status": "generating", "error": ""}
    v = vrows[0]

    def run():
        try:
            import json
            from pathlib import Path
            from core.produce import script_gen
            from core.produce.project import Project

            dna_path     = Path(ch["dna_path"])
            dna          = json.loads(dna_path.read_text(encoding="utf-8"))
            topic        = v.get("topic", "")
            brief        = v.get("brief", "")
            duration     = body.duration_hint or ch.get("default_duration") or "10min"
            voice_id     = ch.get("voice_id") or ""
            prod_name    = f"{name}-{video_id}"

            # Auto-resync if DNA predates writing_examples or visual_style_formula
            if not dna.get("writing_examples") or not dna.get("visual_style_formula"):
                from core import channel_dna_synth
                from data.db import db as _db2
                _d2 = _db2()
                _bp_rows = list(_d2["channel_videos"].rows_where(
                    "channel_name = ? AND blueprint_path IS NOT NULL", [name]
                ))
                _bp_paths = [Path(r["blueprint_path"]) for r in _bp_rows if r.get("blueprint_path")]
                if _bp_paths:
                    resync_path = channel_dna_synth.synthesize(name, _bp_paths)
                    dna = json.loads(resync_path.read_text(encoding="utf-8"))
                    # Persist updated dna_path
                    _d2["my_channels"].update(name, {"dna_path": str(resync_path)})
                    _d2.conn.commit()

            # Inject target audience + tone + brief into the DNA formula for script gen
            if ch.get("target_audience") or ch.get("tone") or brief:
                sf = dna.setdefault("script_formula", {})
                if ch.get("target_audience"):
                    sf["target_audience"] = ch["target_audience"]
                if ch.get("tone"):
                    sf.setdefault("tone", [ch["tone"]])
                if brief:
                    sf["angle_brief"] = brief

            script = script_gen.generate(dna, topic, duration)

            proj = Project(prod_name)
            if not proj.get("blueprint_path"):
                proj.init(
                    blueprint_path=ch["dna_path"],
                    topic=topic,
                    resolution="4K",
                    voice_id=voice_id,
                    duration_hint=duration,
                )
            proj.script_path.write_text(
                json.dumps(script, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            proj.set("sections_confirmed", True)  # web flow — skip CLI gate

            script_str = json.dumps(script)
            db()["channel_videos"].update(video_id, {
                "script_json":    script_str,
                "script_status":  "ready",
                "production_name": prod_name,
                "status":          "scripted",
            }, alter=True)
            _script_jobs[job_key] = {"status": "done", "error": ""}
        except Exception as e:
            _script_jobs[job_key] = {"status": "error", "error": str(e)}

    threading.Thread(target=run, daemon=True).start()
    return {"status": "generating"}


@router.get("/{name}/videos/{video_id}/script/status")
async def script_job_status(name: str, video_id: int):
    return _script_jobs.get(str(video_id), {"status": "idle", "error": ""})


@router.get("/{name}/videos/{video_id}/script")
async def get_script(name: str, video_id: int):
    import json
    d = db()
    rows = list(d["channel_videos"].rows_where("id = ? AND channel_name = ?", [video_id, name]))
    if not rows:
        raise HTTPException(404, "Video not found.")
    v = rows[0]
    raw = v.get("script_json") or ""
    if not raw:
        raise HTTPException(404, "No script yet.")
    return {"script": json.loads(raw), "script_status": v.get("script_status", "ready")}


@router.patch("/{name}/videos/{video_id}/script")
async def save_script(name: str, video_id: int, body: ScriptSave):
    import json
    from pathlib import Path
    from core.produce.project import Project

    d = db()
    rows = list(d["channel_videos"].rows_where("id = ? AND channel_name = ?", [video_id, name]))
    if not rows:
        raise HTTPException(404, "Video not found.")
    v = rows[0]

    # Validate JSON
    try:
        parsed = json.loads(body.script_json)
    except ValueError as e:
        raise HTTPException(400, f"Invalid JSON: {e}")

    # Also write to project file
    prod_name = v.get("production_name") or f"{name}-{video_id}"
    proj = Project(prod_name)
    proj.script_path.write_text(
        json.dumps(parsed, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    d["channel_videos"].update(video_id, {"script_json": body.script_json}, alter=True)
    return {"ok": True}


@router.post("/{name}/videos/{video_id}/script/approve")
async def approve_script(name: str, video_id: int):
    d = db()
    rows = list(d["channel_videos"].rows_where("id = ? AND channel_name = ?", [video_id, name]))
    if not rows:
        raise HTTPException(404, "Video not found.")
    d["channel_videos"].update(video_id, {"script_status": "approved"}, alter=True)
    return {"ok": True}


# ── Gated section production ──────────────────────────────────────────────────

def _load_section(video_id: int, name: str, sid: str):
    """Helper: load Project + section dict for a video."""
    import json
    from core.produce.project import Project

    d = db()
    vrows = list(d["channel_videos"].rows_where("id = ? AND channel_name = ?", [video_id, name]))
    if not vrows:
        return None, None, None
    v = vrows[0]
    prod_name = v.get("production_name") or f"{name}-{video_id}"
    proj = Project(prod_name)
    if not proj.script_path.exists():
        return None, None, None
    script = json.loads(proj.script_path.read_text(encoding="utf-8"))
    section = next((s for s in script.get("sections", []) if s["id"] == sid), None)
    return proj, section, v


@router.post("/{name}/videos/{video_id}/produce/section/{sid}")
async def start_section_produce(name: str, video_id: int, sid: str):
    job_key = f"{video_id}:{sid}"
    if _section_jobs.get(job_key, {}).get("status") == "producing":
        return {"status": "already_running"}

    proj, section, v = _load_section(video_id, name, sid)
    if not proj or not section:
        raise HTTPException(404, "Section not found. Generate script first.")

    _section_jobs[job_key] = {"status": "producing", "current": "Starting…", "error": "", "mp4_path": ""}

    def run():
        try:
            from core.produce.pipeline import produce_section_for_web
            mp4 = produce_section_for_web(
                project=proj,
                section=section,
                redo=False,
                progress=lambda msg: _section_jobs.__setitem__(
                    job_key, {**_section_jobs.get(job_key, {}), "current": msg}
                ),
            )
            path = str(mp4) if mp4 else ""
            _section_jobs[job_key] = {"status": "done", "current": "Section complete.", "error": "", "mp4_path": path}
            if mp4:
                proj.set_section_status(sid, "produced")   # user must approve to unlock next
        except Exception as e:
            _section_jobs[job_key] = {"status": "error", "current": "", "error": str(e), "mp4_path": ""}

    threading.Thread(target=run, daemon=True).start()
    return {"status": "producing"}


@router.post("/{name}/videos/{video_id}/produce/section/{sid}/approve")
async def approve_section(name: str, video_id: int, sid: str):
    """User approves a completed section — unlocks the next one."""
    proj, section, v = _load_section(video_id, name, sid)
    if not proj:
        raise HTTPException(404, "Section not found.")
    proj.set_section_status(sid, "approved")
    return {"ok": True}


@router.get("/{name}/videos/{video_id}/produce/section/{sid}/status")
async def section_produce_status(name: str, video_id: int, sid: str):
    job_key = f"{video_id}:{sid}"
    job = _section_jobs.get(job_key, {"status": "idle", "current": "", "error": "", "mp4_path": ""})
    # Build web URL if mp4 exists
    url = ""
    if job.get("mp4_path"):
        from pathlib import Path
        from core.produce.project import Project
        d = db()
        rows = list(d["channel_videos"].rows_where("id = ?", [video_id]))
        prod_name = (rows[0].get("production_name") if rows else None) or f"{name}-{video_id}"
        url = f"/productions/{prod_name}/sections/{sid}/section.mp4"
    return {**job, "mp4_url": url}


@router.post("/{name}/videos/{video_id}/produce/section/{sid}/redo")
async def redo_section(name: str, video_id: int, sid: str):
    job_key = f"{video_id}:{sid}"
    proj, section, v = _load_section(video_id, name, sid)
    if not proj or not section:
        raise HTTPException(404, "Section not found.")

    _section_jobs[job_key] = {"status": "producing", "current": "Redoing section…", "error": "", "mp4_path": ""}

    def run():
        try:
            from core.produce.pipeline import produce_section_for_web
            mp4 = produce_section_for_web(
                project=proj,
                section=section,
                redo=True,
                progress=lambda msg: _section_jobs.__setitem__(
                    job_key, {**_section_jobs.get(job_key, {}), "current": msg}
                ),
            )
            path = str(mp4) if mp4 else ""
            _section_jobs[job_key] = {"status": "done", "current": "Redo complete.", "error": "", "mp4_path": path}
            if mp4:
                proj.set_section_status(sid, "produced")  # needs re-approval
        except Exception as e:
            _section_jobs[job_key] = {"status": "error", "current": "", "error": str(e), "mp4_path": ""}

    threading.Thread(target=run, daemon=True).start()
    return {"status": "producing"}


@router.get("/{name}/videos/{video_id}/produce/sections")
async def list_produce_sections(name: str, video_id: int):
    import json
    from core.produce.project import Project

    d = db()
    rows = list(d["channel_videos"].rows_where("id = ? AND channel_name = ?", [video_id, name]))
    if not rows:
        raise HTTPException(404, "Video not found.")
    v = rows[0]
    prod_name = v.get("production_name") or f"{name}-{video_id}"
    proj = Project(prod_name)

    if not proj.script_path.exists():
        return {"sections": [], "prod_name": prod_name}

    script = json.loads(proj.script_path.read_text(encoding="utf-8"))
    result = []
    for sec in script.get("sections", []):
        sid      = sec["id"]
        job_key  = f"{video_id}:{sid}"
        job      = dict(_section_jobs.get(job_key, {"status": "idle", "current": "", "error": "", "mp4_path": ""}))
        sec_mp4  = proj.section_dir(sid) / "section.mp4"
        if sec_mp4.exists() and not job.get("mp4_path"):
            job["mp4_path"] = str(sec_mp4)
            job["status"]   = "done"
        url = f"/productions/{prod_name}/sections/{sid}/section.mp4" if job.get("mp4_path") else ""
        result.append({
            "id":          sid,
            "label":       sec.get("label", sid),
            "scene_count": len(sec.get("scenes", [])),
            "scenes":      sec.get("scenes", []),  # for prompt sheet
            "status":      proj.section_status(sid),
            "job":         {**job, "mp4_url": url},
        })
    return {"sections": result, "prod_name": prod_name}


# ── Final assembly ────────────────────────────────────────────────────────────

@router.post("/{name}/videos/{video_id}/produce/final")
async def start_final_assembly(name: str, video_id: int):
    d = db()
    rows = list(d["channel_videos"].rows_where("id = ? AND channel_name = ?", [video_id, name]))
    if not rows:
        raise HTTPException(404, "Video not found.")
    v = rows[0]
    prod_name = v.get("production_name") or f"{name}-{video_id}"

    job_key = str(video_id)
    if _final_jobs.get(job_key, {}).get("status") == "assembling":
        return {"status": "already_running"}

    _final_jobs[job_key] = {"status": "assembling", "current": "Starting final assembly…", "error": "", "output_path": "", "output_url": ""}

    def run():
        try:
            import json
            from core.produce.project import Project
            from core.produce import assembler

            proj = Project(prod_name)
            script = json.loads(proj.script_path.read_text(encoding="utf-8"))
            section_videos = []
            for sec in script.get("sections", []):
                mp4 = proj.section_dir(sec["id"]) / "section.mp4"
                if mp4.exists():
                    section_videos.append(mp4)

            if not section_videos:
                _final_jobs[job_key] = {"status": "error", "current": "", "error": "No completed sections found.", "output_path": "", "output_url": ""}
                return

            final = assembler.assemble_final(section_videos, proj.final_output(), None)
            url   = f"/productions/{prod_name}/output/final_{proj.resolution}.mp4"
            db()["channel_videos"].update(video_id, {"status": "done", "final_mp4_path": str(final)}, alter=True)
            _final_jobs[job_key] = {"status": "done", "current": "Assembly complete.", "error": "", "output_path": str(final), "output_url": url}
        except Exception as e:
            _final_jobs[job_key] = {"status": "error", "current": "", "error": str(e), "output_path": "", "output_url": ""}

    threading.Thread(target=run, daemon=True).start()
    return {"status": "assembling"}


@router.get("/{name}/videos/{video_id}/produce/final/status")
async def final_status(name: str, video_id: int):
    return _final_jobs.get(str(video_id), {"status": "idle", "current": "", "error": "", "output_path": "", "output_url": ""})
