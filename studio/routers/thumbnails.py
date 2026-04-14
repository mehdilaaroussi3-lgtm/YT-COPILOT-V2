"""/api/generate, /api/progress, /api/refine, /api/thumbnails/history."""
from __future__ import annotations

import asyncio
import json
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Body, File, Form, UploadFile
from fastapi.responses import StreamingResponse

from data.db import db
from studio.routers.common import save_upload, to_output_url, url_to_output_path

router = APIRouter()

# Generation jobs
_jobs: dict[str, dict] = {}


@router.post("/api/generate")
async def api_generate(
    title: str = Form(...),
    channel: str = Form("default"),
    script: Optional[str] = Form(None),
    no_text: bool = Form(False),
    variants: int = Form(1),
    style_channel_id: Optional[str] = Form(None),
    sketch: Optional[UploadFile] = File(None),
    reference: Optional[UploadFile] = File(None),
) -> dict:
    job_id = uuid.uuid4().hex[:12]
    _jobs[job_id] = {
        "status": "queued", "events": [], "variant_events": [],
        "result": None, "error": None, "cancelled": False,
    }

    sketch_path = await save_upload(sketch)
    reference_path = await save_upload(reference)

    asyncio.create_task(_run_generate(
        job_id, title, channel, script,
        sketch_path, reference_path, no_text, variants, style_channel_id,
    ))
    return {"job_id": job_id}


def _json_safe(v):
    """Coerce filesystem-path-like values to strings so JSON serialization
    never blows up. sqlite-utils and FastAPI both call json.dumps on
    whatever we hand them, and Path objects are not serializable."""
    from pathlib import PurePath
    if isinstance(v, PurePath):
        return str(v)
    if isinstance(v, dict):
        return {k: _json_safe(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_json_safe(x) for x in v]
    return v


async def _run_generate(job_id, title, channel, script,
                         sketch, reference, no_text, variants, style_channel_id):
    import traceback
    from generators.pipeline import run_pipeline
    job = _jobs[job_id]
    job["status"] = "running"

    def progress(msg: str) -> None:
        job["events"].append(str(msg))

    def variant_done(data: dict) -> None:
        payload = _json_safe(dict(data))
        if payload.get("file_path"):
            payload["url"] = to_output_url(payload["file_path"])
        job["variant_events"].append(payload)

    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(
            None, lambda: run_pipeline(
                title=title, channel=channel,
                script=script, sketch=sketch, reference=reference,
                no_text=no_text, variants=variants,
                style_channel_id=style_channel_id or None,
                do_mockup=False,
                on_progress=progress,
                on_variant_done=variant_done,
                should_cancel=lambda: job["cancelled"],
            ),
        )
        job["result"] = _json_safe(_serialize(result))
        job["status"] = "done"
    except Exception as e:  # noqa: BLE001
        tb = traceback.format_exc()
        # Full traceback to the console so we can audit; short message to client.
        print(f"[pipeline error] job={job_id}\n{tb}")
        job["events"].append(f"Error: {e}")
        job["status"] = "error"
        job["error"] = str(e)


def _serialize(r) -> dict:
    return {
        "title": r.title,
        "channel": r.channel,
        "niche": r.niche,
        "output_dir": r.output_dir,
        "text_hook": r.text_hook,
        "pairing_score": r.pairing_score,
        "pairing_issues": r.pairing_issues,
        "variants": [{
            "variant": v.variant,
            "url": to_output_url(v.file_path),
            "score": v.score,
            "issues": v.score_issues,
        } for v in r.variants],
        "mockup_dark": to_output_url(r.mockup_dark),
        "mockup_light": to_output_url(r.mockup_light),
    }


@router.get("/api/progress/{job_id}")
async def progress_stream(job_id: str):
    if job_id not in _jobs:
        return {"error": "unknown job"}

    async def events():
        last_log = 0
        last_var = 0
        while True:
            job = _jobs[job_id]
            while last_log < len(job["events"]):
                yield f"data: {json.dumps({'msg': str(job['events'][last_log])})}\n\n"
                last_log += 1
            while last_var < len(job["variant_events"]):
                v = _json_safe(job["variant_events"][last_var])
                yield f"event: variant\ndata: {json.dumps(v)}\n\n"
                last_var += 1
            if job["status"] == "done":
                yield f"event: done\ndata: {json.dumps(_json_safe(job['result']))}\n\n"
                return
            if job["status"] == "error":
                yield f"event: error\ndata: {json.dumps({'error': str(job['error'])})}\n\n"
                return
            await asyncio.sleep(0.3)

    return StreamingResponse(events(), media_type="text/event-stream")


@router.post("/api/generate/{job_id}/cancel")
async def cancel_job(job_id: str) -> dict:
    if job_id not in _jobs:
        return {"error": "unknown job"}
    _jobs[job_id]["cancelled"] = True
    return {"ok": True}


@router.post("/api/refine")
async def api_refine(
    image_url: str = Form(...),
    instruction: str = Form(...),
    reference: Optional[UploadFile] = File(None),
) -> dict:
    from generators.refiner import refine_thumbnail
    src = url_to_output_path(image_url)
    if not src.exists():
        return {"error": f"file not found: {src}"}
    ref_path = await save_upload(reference)
    try:
        out = refine_thumbnail(src, instruction, extra_reference=ref_path)
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)}
    return {"url": to_output_url(out)}


@router.get("/api/thumbnails/history")
def thumbnails_history(channel: str | None = None, limit: int = 120) -> dict:
    d = db()
    if channel:
        rows = list(d["generations"].rows_where(
            "channel = ?", [channel],
            order_by="created_at desc", limit=limit,
        ))
    else:
        rows = list(d["generations"].rows_where(
            order_by="created_at desc", limit=limit,
        ))
    for r in rows:
        r["url"] = to_output_url(r.get("file_path"))
    return {"items": rows}
