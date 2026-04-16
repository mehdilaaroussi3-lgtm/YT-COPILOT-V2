"""Templates router — content format template CRUD + analysis."""
from __future__ import annotations

import json
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.template_analyzer import start_analysis_background
from data.db import db as get_db

router = APIRouter(prefix="/api/templates", tags=["templates"])

# In-memory job tracking (analysis jobs)
_analysis_jobs: dict[str, dict] = {}


class TemplateCreate(BaseModel):
    name: str
    description: str = ""


@router.get("")
def list_templates():
    """List all templates (newest first)."""
    d = get_db()
    rows = list(d["templates"].rows_where(order_by="-created_at"))

    # Parse JSON fields
    for row in rows:
        row["example_channels"] = json.loads(row.get("example_channels", "[]"))
        row["example_video_ids"] = json.loads(row.get("example_video_ids", "[]"))

    return {"templates": rows}


@router.post("")
def create_template(req: TemplateCreate):
    """Create a new template (status: draft)."""
    d = get_db()

    template_id = uuid.uuid4().hex[:12]
    now = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()

    d["templates"].insert({
        "id": template_id,
        "name": req.name,
        "description": req.description or "",
        "status": "draft",
        "stage": "",
        "stage_pct": 0,
        "example_channels": "[]",
        "example_video_ids": "[]",
        "dna_path": "",
        "reddit_findings": "{}",
        "prompt_helpers": "{}",
        "error": "",
        "created_at": now,
        "updated_at": now,
    })

    return {"id": template_id, "name": req.name, "status": "draft"}


@router.get("/{template_id}")
def template_detail(template_id: str):
    """Get full template detail."""
    d = get_db()
    row = d["templates"].get(template_id)

    if not row:
        raise HTTPException(404, "Template not found")

    # Parse JSON fields
    row["example_channels"] = json.loads(row.get("example_channels", "[]"))
    row["example_video_ids"] = json.loads(row.get("example_video_ids", "[]"))
    row["reddit_findings"] = json.loads(row.get("reddit_findings", "{}"))
    row["prompt_helpers"] = json.loads(row.get("prompt_helpers", "{}"))

    return row


@router.post("/{template_id}/analyze")
def analyze_template(template_id: str):
    """Trigger background analysis pipeline."""
    d = get_db()
    row = d["templates"].get(template_id)

    if not row:
        raise HTTPException(404, "Template not found")

    # Idempotent — if already analyzing or ready, return current status
    if row["status"] in ("analyzing", "ready"):
        return {"ok": True, "status": row["status"]}

    # Set status to analyzing and start background thread
    import datetime
    d["templates"].update(
        template_id,
        {
            "status": "analyzing",
            "stage": "Starting...",
            "stage_pct": 0,
            "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
    )

    # Kick off background analysis
    start_analysis_background(template_id, row["name"])

    return {"ok": True}


@router.get("/{template_id}/status")
def template_status(template_id: str):
    """Poll analysis progress."""
    d = get_db()
    row = d["templates"].get(template_id)

    if not row:
        raise HTTPException(404, "Template not found")

    return {
        "status": row["status"],
        "stage": row.get("stage", ""),
        "stage_pct": row.get("stage_pct", 0),
        "error": row.get("error", ""),
    }


@router.delete("/{template_id}")
def delete_template(template_id: str):
    """Delete template and remove data directory."""
    d = get_db()
    row = d["templates"].get(template_id)

    if not row:
        raise HTTPException(404, "Template not found")

    # Remove data directory
    tpl_dir = Path("data/templates") / template_id
    if tpl_dir.exists():
        import shutil
        shutil.rmtree(tpl_dir, ignore_errors=True)

    # Remove from DB
    d["templates"].delete_where("id = ?", [template_id])

    return {"ok": True}


@router.get("/{template_id}/dna")
def template_dna(template_id: str):
    """Get raw dna.json content."""
    d = get_db()
    row = d["templates"].get(template_id)

    if not row:
        raise HTTPException(404, "Template not found")

    dna_path = Path(row.get("dna_path", ""))
    if not dna_path.exists():
        raise HTTPException(400, "Template DNA not yet generated")

    return json.loads(dna_path.read_text("utf-8"))
