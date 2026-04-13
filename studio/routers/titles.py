"""/api/titles — generate + history + pin."""
from __future__ import annotations

from fastapi import APIRouter, Body

from core import title_generator

router = APIRouter(prefix="/api/titles")


@router.post("")
def generate(payload: dict = Body(...)) -> dict:
    channel = (payload.get("channel") or "default").strip()
    idea = (payload.get("idea") or "").strip()
    if not idea:
        return {"error": "idea required"}
    count = int(payload.get("count", 6))
    try:
        items = title_generator.generate_titles(channel, idea, count=count)
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)}
    return {"items": items}


@router.get("/history")
def history(channel: str | None = None, limit: int = 100) -> dict:
    return {"items": title_generator.history(channel, limit)}


@router.post("/{title_id}/pin")
def pin(title_id: int) -> dict:
    return {"pinned": title_generator.toggle_pin(title_id)}
