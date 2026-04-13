"""/api/winners — indexed/style-tagged outliers with similarity search."""
from __future__ import annotations

import json

from fastapi import APIRouter

from data.db import db
from studio.routers.common import to_cache_url

router = APIRouter(prefix="/api/winners")


@router.get("")
def list_winners(niche: str | None = None, limit: int = 60) -> dict:
    """Return outlier thumbnails that have been Vision-indexed (style_tags present)."""
    d = db()
    sql = """
    SELECT t.video_id, t.file_path, t.description, t.style_tags, t.colors,
           t.text_amount, v.title, v.outlier_score, v.channel_id
    FROM thumbnails t
    JOIN videos v ON v.video_id = t.video_id
    WHERE t.style_tags IS NOT NULL AND t.style_tags != ''
    ORDER BY v.outlier_score DESC
    LIMIT ?
    """
    rows = list(d.query(sql, [limit]))
    for r in rows:
        r["thumb_url"] = to_cache_url(r.get("file_path"))
        try:
            r["colors_list"] = json.loads(r.get("colors") or "[]")
        except json.JSONDecodeError:
            r["colors_list"] = []
        r["tags_list"] = [t.strip() for t in (r.get("style_tags") or "").split(",") if t.strip()]
    return {"items": rows}


@router.get("/similar/{video_id}")
def similar(video_id: str, limit: int = 12) -> dict:
    """Find thumbnails with overlapping style_tags."""
    d = db()
    if video_id not in d["thumbnails"].pks:
        return {"items": []}
    me = d["thumbnails"].get(video_id)
    my_tags = {t.strip().lower() for t in (me.get("style_tags") or "").split(",") if t.strip()}

    if not my_tags:
        return {"items": []}

    rows = list(d["thumbnails"].rows_where(
        "style_tags IS NOT NULL AND style_tags != '' AND video_id != ?",
        [video_id],
    ))
    scored = []
    for r in rows:
        tags = {t.strip().lower() for t in (r.get("style_tags") or "").split(",") if t.strip()}
        overlap = len(my_tags & tags)
        if overlap > 0:
            scored.append((overlap, r))
    scored.sort(key=lambda x: x[0], reverse=True)
    out = []
    for overlap, r in scored[:limit]:
        r["thumb_url"] = to_cache_url(r.get("file_path"))
        r["tag_overlap"] = overlap
        out.append(r)
    return {"items": out}
