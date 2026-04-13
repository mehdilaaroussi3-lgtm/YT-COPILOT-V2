"""/api/trackers — user-added channel tracking."""
from __future__ import annotations

import asyncio
import json
import uuid
from typing import Optional

from fastapi import APIRouter, Body
from fastapi.responses import StreamingResponse

from core import trackers as trackers_core
from agents.outlier_discovery import OutlierDiscoveryAgent

router = APIRouter(prefix="/api/trackers")

# Job store for scan progress SSE
_scan_jobs: dict[str, dict] = {}


@router.get("")
def list_tracked() -> dict:
    return {"items": trackers_core.list_tracked()}


@router.post("")
def add(payload: dict = Body(...)) -> dict:
    handle = (payload.get("handle") or "").strip()
    if not handle:
        return {"error": "handle required"}
    try:
        row = trackers_core.add_tracked(handle, payload.get("niche_override", ""))
    except ValueError as e:
        return {"error": str(e)}
    return {"item": row}


@router.delete("/{channel_id}")
def remove(channel_id: str) -> dict:
    trackers_core.remove_tracked(channel_id)
    return {"ok": True}


@router.patch("/{channel_id}/default")
def set_default(channel_id: str) -> dict:
    trackers_core.set_default(channel_id)
    return {"ok": True}


@router.post("/{channel_id}/resummarize")
def resummarize(channel_id: str) -> dict:
    """Re-run AI synthesis for this channel's 'About' text."""
    from core.channel_summary import synthesize
    summary = synthesize(channel_id)
    return {"ai_summary": summary}


@router.post("/{channel_id}/refresh")
def refresh(channel_id: str) -> dict:
    """Kick off background outlier scan, return job_id for SSE."""
    job_id = uuid.uuid4().hex[:12]
    _scan_jobs[job_id] = {"status": "queued", "events": [], "result": None, "error": None}
    tracked = {r["channel_id"]: r for r in trackers_core.list_tracked()}
    if channel_id not in tracked:
        return {"error": "channel not tracked"}
    name = tracked[channel_id].get("name") or channel_id
    asyncio.create_task(_run_scan(job_id, channel_id, name))
    return {"job_id": job_id}


async def _run_scan(job_id: str, channel_id: str, name: str) -> None:
    job = _scan_jobs[job_id]
    job["status"] = "running"

    def log(msg: str) -> None:
        job["events"].append(msg)

    loop = asyncio.get_event_loop()
    try:
        log(f"Connecting to YouTube API for {name}...")
        agent = OutlierDiscoveryAgent()
        log("Computing channel median + outlier scores...")
        outliers = await loop.run_in_executor(
            None, lambda: agent.scan_channel(channel_id, name, min_score=2.0, download=True)
        )
        log(f"Found {len(outliers)} outliers (≥2x) — thumbnails cached.")
        trackers_core.mark_scanned(channel_id)
        job["result"] = {"outliers": len(outliers)}
        job["status"] = "done"
    except Exception as e:  # noqa: BLE001
        job["status"] = "error"
        job["error"] = str(e)


@router.get("/scan/{job_id}")
async def scan_progress(job_id: str):
    if job_id not in _scan_jobs:
        return {"error": "unknown job"}

    async def events():
        last = 0
        while True:
            job = _scan_jobs[job_id]
            while last < len(job["events"]):
                yield f"data: {json.dumps({'msg': job['events'][last]})}\n\n"
                last += 1
            if job["status"] == "done":
                yield f"event: done\ndata: {json.dumps(job['result'])}\n\n"
                return
            if job["status"] == "error":
                yield f"event: error\ndata: {json.dumps({'error': job['error']})}\n\n"
                return
            await asyncio.sleep(0.4)

    return StreamingResponse(events(), media_type="text/event-stream")
