"""/api/ideas — async job system so generations survive tab-switches."""
from __future__ import annotations

import asyncio
import uuid

from fastapi import APIRouter, Body

from core import idea_generator

router = APIRouter(prefix="/api/ideas")

# job_id → {status, items, error, started_at}
_jobs: dict[str, dict] = {}


@router.post("")
async def generate(payload: dict = Body(...)) -> dict:
    channel = (payload.get("channel") or "default").strip()
    topic = (payload.get("topic") or "").strip() or None
    count = int(payload.get("count", 6))

    job_id = uuid.uuid4().hex[:12]
    _jobs[job_id] = {"status": "running", "items": [], "error": None}
    asyncio.create_task(_run_ideas(job_id, channel, topic, count))
    return {"job_id": job_id}


async def _run_ideas(job_id: str, channel: str, topic: str | None, count: int):
    job = _jobs[job_id]
    loop = asyncio.get_event_loop()
    try:
        items = await loop.run_in_executor(
            None, lambda: idea_generator.generate_ideas(channel, topic, count=count),
        )
        job["items"] = items
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
        "items": job.get("items", []),
        "error": job.get("error"),
    }


@router.get("/history")
def history(channel: str | None = None, limit: int = 80) -> dict:
    return {"items": idea_generator.history(channel, limit)}
