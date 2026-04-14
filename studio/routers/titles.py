"""/api/titles — async job system so generations survive tab-switches."""
from __future__ import annotations

import asyncio
import uuid

from fastapi import APIRouter, Body

from core import title_generator

router = APIRouter(prefix="/api/titles")

_jobs: dict[str, dict] = {}


@router.post("")
async def generate(payload: dict = Body(...)) -> dict:
    channel = (payload.get("channel") or "default").strip()
    idea = (payload.get("idea") or "").strip()
    if not idea:
        return {"error": "idea required"}
    per_source = int(payload.get("count", 10))

    job_id = uuid.uuid4().hex[:12]
    _jobs[job_id] = {
        "status": "running",
        "channel_titles": [],
        "outlier_titles": [],
        "error": None,
    }
    asyncio.create_task(_run_titles(job_id, channel, idea, per_source))
    return {"job_id": job_id}


async def _run_titles(job_id: str, channel: str, idea: str, per_source: int):
    job = _jobs[job_id]
    loop = asyncio.get_event_loop()
    try:
        dual = await loop.run_in_executor(
            None, lambda: title_generator.generate_titles_dual(channel, idea, per_source=per_source),
        )
        job["channel_titles"] = dual.get("channel_titles", [])
        job["outlier_titles"] = dual.get("outlier_titles", [])
        job["status"] = "done"
    except Exception as e:  # noqa: BLE001
        job["error"] = str(e)
        job["status"] = "error"


@router.get("/status/{job_id}")
def status(job_id: str) -> dict:
    job = _jobs.get(job_id)
    if not job:
        return {"status": "unknown"}
    return {
        "status": job["status"],
        "channel_titles": job.get("channel_titles", []),
        "outlier_titles": job.get("outlier_titles", []),
        "items": job.get("channel_titles", []) + job.get("outlier_titles", []),
        "error": job.get("error"),
    }


@router.get("/history")
def history(channel: str | None = None, limit: int = 100) -> dict:
    return {"items": title_generator.history(channel, limit)}


@router.post("/{title_id}/pin")
def pin(title_id: int) -> dict:
    return {"pinned": title_generator.toggle_pin(title_id)}
