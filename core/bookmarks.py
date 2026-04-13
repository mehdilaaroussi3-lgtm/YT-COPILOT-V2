"""Bookmarks + folders CRUD.

Unified folder system — a single folder can contain both outlier reference
thumbnails (source='reference', joins videos+thumbnails) AND user-generated
thumbnails (source='generated', joins generations). Folders organise by topic.
"""
from __future__ import annotations

import datetime as dt
from typing import Any

from data.db import db


DEFAULT_COLORS = ["#2e4cf0", "#ff6b35", "#2f9e44", "#b23ebf", "#d8a300", "#0f8988"]


# ---- Folders ----------------------------------------------------------------

def list_folders() -> list[dict[str, Any]]:
    d = db()
    folders = list(d["folders"].rows_where(order_by="created_at desc"))
    # Attach item counts
    for f in folders:
        f["item_count"] = d["bookmarks"].count_where("folder_id = ?", [f["id"]])
    return folders


def create_folder(name: str, color: str | None = None) -> dict[str, Any]:
    d = db()
    next_color = color or DEFAULT_COLORS[d["folders"].count % len(DEFAULT_COLORS)]
    row = {
        "name": name.strip() or "Untitled",
        "color": next_color,
        "created_at": dt.datetime.now(dt.UTC).isoformat(),
    }
    d["folders"].insert(row, alter=True)
    return {**row, "id": d["folders"].last_pk, "item_count": 0}


def delete_folder(folder_id: int) -> None:
    d = db()
    d["bookmarks"].delete_where("folder_id = ?", [folder_id])
    d["folders"].delete(folder_id)


def rename_folder(folder_id: int, name: str) -> None:
    d = db()
    d["folders"].update(folder_id, {"name": name})


# ---- Bookmarks --------------------------------------------------------------

def add_reference(folder_id: int, video_id: str, note: str = "") -> dict[str, Any]:
    d = db()
    row = {
        "folder_id": folder_id,
        "source": "reference",
        "video_id": video_id,
        "generation_id": None,
        "note": note,
        "added_at": dt.datetime.now(dt.UTC).isoformat(),
    }
    d["bookmarks"].insert(row, alter=True)
    return {**row, "id": d["bookmarks"].last_pk}


def add_generation(folder_id: int, generation_id: int,
                    note: str = "") -> dict[str, Any]:
    d = db()
    row = {
        "folder_id": folder_id,
        "source": "generated",
        "video_id": None,
        "generation_id": generation_id,
        "note": note,
        "added_at": dt.datetime.now(dt.UTC).isoformat(),
    }
    d["bookmarks"].insert(row, alter=True)
    return {**row, "id": d["bookmarks"].last_pk}


def remove_bookmark(bookmark_id: int) -> None:
    d = db()
    d["bookmarks"].delete(bookmark_id)


def list_in_folder(folder_id: int) -> list[dict[str, Any]]:
    """Return hydrated bookmarks — each row enriched with source data."""
    d = db()
    bookmarks = list(d["bookmarks"].rows_where(
        "folder_id = ?", [folder_id], order_by="added_at desc",
    ))
    out = []
    for b in bookmarks:
        hydrated = dict(b)
        if b["source"] == "reference" and b.get("video_id"):
            vid = d["videos"].get(b["video_id"]) if b["video_id"] in d["videos"].pks else None
            thumb = d["thumbnails"].get(b["video_id"]) if b["video_id"] in d["thumbnails"].pks else None
            hydrated["video"] = vid
            hydrated["thumbnail"] = thumb
        elif b["source"] == "generated" and b.get("generation_id"):
            gen = d["generations"].get(b["generation_id"]) if b["generation_id"] in d["generations"].pks else None
            hydrated["generation"] = gen
        out.append(hydrated)
    return out
