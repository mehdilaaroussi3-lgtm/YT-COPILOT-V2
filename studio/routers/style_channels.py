"""/api/style-channels — channels available as a 'style from' source."""
from __future__ import annotations

from fastapi import APIRouter

from core.style_channel import list_style_channels

router = APIRouter()


@router.get("/api/style-channels")
def style_channels() -> dict:
    return {"items": list_style_channels()}
