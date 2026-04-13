"""/api/ideas — generate + history."""
from __future__ import annotations

from fastapi import APIRouter, Body

from core import idea_generator

router = APIRouter(prefix="/api/ideas")


@router.post("")
def generate(payload: dict = Body(...)) -> dict:
    channel = (payload.get("channel") or "default").strip()
    topic = (payload.get("topic") or "").strip() or None
    count = int(payload.get("count", 6))
    try:
        items = idea_generator.generate_ideas(channel, topic, count=count)
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)}
    return {"items": items}


@router.get("/history")
def history(channel: str | None = None, limit: int = 80) -> dict:
    return {"items": idea_generator.history(channel, limit)}
