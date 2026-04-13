"""/api/folders, /api/bookmarks — unified folder system."""
from __future__ import annotations

from fastapi import APIRouter, Body

from core import bookmarks as bm
from studio.routers.common import to_cache_url, to_output_url

router = APIRouter()


@router.get("/api/folders")
def list_folders() -> dict:
    return {"items": bm.list_folders()}


@router.post("/api/folders")
def create_folder(payload: dict = Body(...)) -> dict:
    name = (payload.get("name") or "").strip()
    return {"item": bm.create_folder(name, payload.get("color"))}


@router.delete("/api/folders/{folder_id}")
def delete_folder(folder_id: int) -> dict:
    bm.delete_folder(folder_id)
    return {"ok": True}


@router.patch("/api/folders/{folder_id}")
def rename_folder(folder_id: int, payload: dict = Body(...)) -> dict:
    name = (payload.get("name") or "").strip()
    if name:
        bm.rename_folder(folder_id, name)
    return {"ok": True}


@router.get("/api/bookmarks")
def list_bookmarks(folder_id: int) -> dict:
    rows = bm.list_in_folder(folder_id)
    for r in rows:
        if r.get("thumbnail"):
            r["thumb_url"] = to_cache_url(r["thumbnail"].get("file_path"))
        elif r.get("generation"):
            r["thumb_url"] = to_output_url(r["generation"].get("file_path"))
        else:
            r["thumb_url"] = ""
    return {"items": rows}


@router.post("/api/bookmarks")
def add_bookmark(payload: dict = Body(...)) -> dict:
    folder_id = int(payload["folder_id"])
    source = payload.get("source", "reference")
    if source == "reference":
        return {"item": bm.add_reference(folder_id, payload["video_id"], payload.get("note", ""))}
    return {"item": bm.add_generation(folder_id, int(payload["generation_id"]), payload.get("note", ""))}


@router.delete("/api/bookmarks/{bookmark_id}")
def remove_bookmark(bookmark_id: int) -> dict:
    bm.remove_bookmark(bookmark_id)
    return {"ok": True}
