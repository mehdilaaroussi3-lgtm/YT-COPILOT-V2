"""/api/outliers — random, search, detail."""
from __future__ import annotations

from fastapi import APIRouter

from core.outliers import get_outlier, random_outliers, search_outliers
from studio.routers.common import to_cache_url

router = APIRouter(prefix="/api/outliers")


def _decorate(items: list[dict]) -> list[dict]:
    for it in items:
        it["thumb_url"] = to_cache_url(it.get("thumbnail_path"))
    return items


@router.get("/random")
def random(limit: int = 12, min_score: float = 2.0) -> dict:
    return {"items": _decorate(random_outliers(limit=limit, min_score=min_score))}


@router.get("/search")
def search(q: str = "", niche: str | None = None,
            channel_id: str | None = None, limit: int = 60) -> dict:
    return {"items": _decorate(search_outliers(q, niche, channel_id, limit))}


@router.get("/{video_id}")
def detail(video_id: str) -> dict:
    item = get_outlier(video_id)
    if not item:
        return {"error": "not found"}
    item["thumb_url"] = to_cache_url(item.get("thumbnail_path"))
    return item
