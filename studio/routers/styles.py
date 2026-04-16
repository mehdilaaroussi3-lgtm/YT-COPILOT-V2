"""/api/styles — unified style CRUD + listing."""
from __future__ import annotations

import base64
import datetime as dt
import json
import mimetypes
import shutil
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from data.db import db

router = APIRouter(prefix="/api/styles", tags=["styles"])

CUSTOM_STYLES_DIR = Path("data/custom_styles")
CUSTOM_STYLES_DIR.mkdir(parents=True, exist_ok=True)


@router.get("")
def list_styles() -> dict:
    """Return all styles (dna + preset + custom) for the picker."""
    from core.style_resolver import list_all_styles

    return {"items": list_all_styles()}


@router.get("/custom")
def list_custom_styles() -> dict:
    """Return presets + custom user-uploaded styles."""
    from core.style_resolver import PRESETS

    items = []

    # Add presets first
    for slug, p in PRESETS.items():
        preview_path = CUSTOM_STYLES_DIR / slug / "preview.png"
        if not preview_path.exists():
            _generate_preset_preview_async(slug, p)

        items.append({
            "id": f"preset:{slug}",
            "uuid": slug,
            "type": "preset",
            "name": p["name"],
            "description": f"Preset style: {p['name']}",
            "style_brief": p["style_brief"],
            "image_prompt_prefix": p["image_prompt_prefix"],
            "image_paths": [],
            "preview_image_path": str(preview_path) if preview_path.exists() else "",
            "created_at": "",
        })

    # Add custom styles
    d = db()
    if "styles" in d.table_names():
        for row in d["styles"].rows_where(order_by="created_at desc"):
            uuid_part = row["id"].split(":", 1)[1] if ":" in row["id"] else row["id"]
            items.append({
                "id": row["id"],
                "uuid": uuid_part,
                "type": "custom",
                "name": row["name"],
                "description": row.get("description", ""),
                "style_brief": row.get("style_brief", ""),
                "image_prompt_prefix": row.get("image_prompt_prefix", ""),
                "image_paths": json.loads(row.get("image_paths") or "[]"),
                "preview_image_path": row.get("preview_image_path") or "",
                "created_at": row.get("created_at", ""),
            })
    return {"items": items}


# ── Job tracking for background tasks ────────────────────────────────────────
_preview_jobs: dict[str, dict] = {}


_preview_queue_lock = threading.Lock() if False else __import__("threading").Lock()
_preview_queue: list[tuple[str, dict]] = []
_preview_worker_started = False


def _generate_preset_preview_async(slug: str, preset: dict) -> None:
    """Queue a preset preview for serialized generation via gemini-3-pro-image-preview.

    All generations go through ONE worker thread (serialized) with 30s pacing
    between requests + aggressive backoff on 429s, staying under rate limits.
    """
    import threading

    global _preview_worker_started

    with _preview_queue_lock:
        # Skip if already queued
        if any(s == slug for s, _ in _preview_queue):
            return
        _preview_queue.append((slug, preset))

        if _preview_worker_started:
            return
        _preview_worker_started = True

    def _worker():
        import time
        from core.produce import image_gen

        while True:
            with _preview_queue_lock:
                if not _preview_queue:
                    break
                slug_, preset_ = _preview_queue.pop(0)

            preview_path = CUSTOM_STYLES_DIR / slug_ / "preview.png"
            if preview_path.exists():
                continue

            preview_path.parent.mkdir(parents=True, exist_ok=True)
            prompt = (
                f"{preset_['image_prompt_prefix']}\n\n"
                f"A YouTube thumbnail in this exact visual style. "
                f"The ONLY text on the thumbnail is the title '{preset_['name']}' — "
                f"rendered large, bold, and prominent. "
                f"Absolutely NO other text, captions, speech bubbles, labels, subtitles, "
                f"or any additional words anywhere on the image. "
                f"No gibberish text, no fake letters, no decorative text. "
                f"Just the clean title '{preset_['name']}' and the visual composition. "
                f"16:9 aspect ratio."
            )

            try:
                image_gen.render(prompt, preview_path, force=True)
            except Exception as e:
                print(f"[preset-preview] {slug_} failed: {e}")

            # Pace between requests to stay under rate limits
            time.sleep(30)

        global _preview_worker_started
        with _preview_queue_lock:
            _preview_worker_started = False

    threading.Thread(target=_worker, daemon=True).start()


@router.post("")
async def create_custom_style(
    name: str = Form(...),
    description: str = Form(""),
    images: list[UploadFile] = File(...),
) -> dict:
    """Create a custom style from 1–5 uploaded reference images.

    Returns the new style_id and metadata.
    """
    if not images or len(images) > 5:
        raise HTTPException(400, "Provide 1–5 reference images")

    style_uuid = uuid.uuid4().hex
    style_id = f"custom:{style_uuid}"
    style_dir = CUSTOM_STYLES_DIR / style_uuid
    style_dir.mkdir(parents=True, exist_ok=True)

    saved_paths: list[str] = []
    for i, upload in enumerate(images):
        suffix = Path(upload.filename or "ref.jpg").suffix or ".jpg"
        dest = style_dir / f"ref_{i}{suffix}"
        try:
            content = await upload.read()
            dest.write_bytes(content)
            saved_paths.append(str(dest))
        except Exception as e:
            shutil.rmtree(style_dir, ignore_errors=True)
            raise HTTPException(500, f"Failed to save image: {e}")

    # Generate a style brief from the uploaded images using Gemini Vision
    style_brief = _generate_custom_brief(saved_paths, name, description)
    image_prompt_prefix = _generate_prompt_prefix(saved_paths, name, description)

    now = dt.datetime.now(dt.UTC).isoformat()
    d = db()
    try:
        d["styles"].insert({
            "id": style_id,
            "style_type": "custom",
            "name": name,
            "description": description,
            "image_prompt_prefix": image_prompt_prefix,
            "style_brief": style_brief,
            "image_paths": json.dumps(saved_paths),
            "created_at": now,
            "updated_at": now,
        })
    except Exception as e:
        shutil.rmtree(style_dir, ignore_errors=True)
        raise HTTPException(500, f"Failed to save style: {e}")

    return {
        "id": style_id,
        "name": name,
        "style_type": "custom",
        "style_brief": style_brief,
    }


@router.delete("/{style_uuid}")
def delete_custom_style(style_uuid: str) -> dict:
    """Delete a custom style."""
    style_id = f"custom:{style_uuid}"
    d = db()

    try:
        if "styles" not in d.table_names():
            raise HTTPException(404, "Style not found")
        row = d["styles"].get(style_id)
    except Exception:
        raise HTTPException(404, "Style not found")

    # Delete images from disk
    style_dir = CUSTOM_STYLES_DIR / style_uuid
    if style_dir.exists():
        shutil.rmtree(style_dir)

    try:
        d["styles"].delete(style_id)
    except Exception:
        pass

    return {"ok": True}


@router.post("/{style_uuid}/preview")
def generate_preview(style_uuid: str) -> dict:
    """Kick off background thread to generate a preview image for a custom style."""
    import threading
    import uuid as uuid_lib

    style_id = f"custom:{style_uuid}"
    d = db()

    try:
        if "styles" not in d.table_names():
            raise HTTPException(404, "Style not found")
        row = d["styles"].get(style_id)
    except Exception:
        raise HTTPException(404, "Style not found")

    if not row:
        raise HTTPException(404, "Style not found")

    job_id = uuid_lib.uuid4().hex
    _preview_jobs[job_id] = {"status": "pending"}

    def _run_preview():
        try:
            from core.produce import image_gen

            name = row.get("name", "Untitled Style")
            image_prompt_prefix = row.get("image_prompt_prefix", "")
            prompt = (
                f"{image_prompt_prefix}\n\n"
                f"A YouTube thumbnail in this exact visual style. "
                f"The ONLY text on the thumbnail is the title '{name}' — "
                f"rendered large, bold, and prominent. "
                f"Absolutely NO other text, captions, speech bubbles, labels, subtitles, "
                f"or any additional words anywhere on the image. "
                f"No gibberish text, no fake letters, no decorative text. "
                f"Just the clean title '{name}' and the visual composition. "
                f"16:9 aspect ratio."
            )
            preview_path = CUSTOM_STYLES_DIR / style_uuid / "preview.png"
            preview_path.parent.mkdir(parents=True, exist_ok=True)
            image_gen.render(prompt, preview_path, force=True)

            # Update DB
            d["styles"].update(style_id, {"preview_image_path": str(preview_path)}, alter=True)
            _preview_jobs[job_id] = {"status": "done", "path": str(preview_path)}
        except Exception as e:
            _preview_jobs[job_id] = {"status": "error", "error": str(e)}

    thread = threading.Thread(target=_run_preview, daemon=True)
    thread.start()

    return {"job_id": job_id}


@router.get("/{style_uuid}/preview/status")
def get_preview_status(style_uuid: str, job_id: str) -> dict:
    """Poll the status of a preview generation job."""
    return _preview_jobs.get(job_id, {"status": "not_found"})


@router.get("/{style_uuid}/preview/image")
def serve_preview_image(style_uuid: str):
    """Serve the generated preview image PNG."""
    from fastapi.responses import FileResponse

    preview_path = CUSTOM_STYLES_DIR / style_uuid / "preview.png"
    if not preview_path.exists():
        raise HTTPException(404, "Preview not generated yet")
    return FileResponse(preview_path, media_type="image/png")


@router.get("/{style_uuid}/ref/{n}")
def serve_ref_image(style_uuid: str, n: int):
    """Serve a reference image by index."""
    from fastapi.responses import FileResponse

    style_id = f"custom:{style_uuid}"
    d = db()

    try:
        if "styles" not in d.table_names():
            raise HTTPException(404, "Style not found")
        row = d["styles"].get(style_id)
    except Exception:
        raise HTTPException(404, "Style not found")

    if not row:
        raise HTTPException(404, "Style not found")

    image_paths: list[str] = json.loads(row.get("image_paths") or "[]")
    if n < 0 or n >= len(image_paths):
        raise HTTPException(404, "Image not found")

    img_path = Path(image_paths[n])
    if not img_path.exists():
        raise HTTPException(404, "Image not found")

    media_type = "image/jpeg"
    if str(img_path).lower().endswith(".png"):
        media_type = "image/png"

    return FileResponse(img_path, media_type=media_type)


class GeneratePromptRequest(BaseModel):
    topic: str


@router.post("/{style_uuid}/generate-prompt")
def generate_style_prompt(style_uuid: str, req: GeneratePromptRequest) -> dict:
    """Generate an image prompt for a given topic in this style."""
    from generators.gemini_text import generate_text

    style_id = f"custom:{style_uuid}"
    d = db()

    try:
        if "styles" not in d.table_names():
            raise HTTPException(404, "Style not found")
        row = d["styles"].get(style_id)
    except Exception:
        raise HTTPException(404, "Style not found")

    if not row:
        raise HTTPException(404, "Style not found")

    image_prompt_prefix = row.get("image_prompt_prefix", "")
    style_brief = row.get("style_brief", "")[:300]

    prompt = (
        f"Write an image generation prompt (60-80 words) for a YouTube thumbnail on topic: '{req.topic}'. "
        f"Apply this style: {image_prompt_prefix}. "
        f"Style brief: {style_brief}. "
        f"Output only the prompt, no preamble."
    )

    result = generate_text(prompt, temperature=0.5)
    return {"prompt": result.strip()}


@router.get("/{style_uuid}")
def get_custom_style(style_uuid: str) -> dict:
    """Get a custom style by UUID."""
    style_id = f"custom:{style_uuid}"
    d = db()

    try:
        if "styles" not in d.table_names():
            raise HTTPException(404, "Style not found")
        row = d["styles"].get(style_id)
    except Exception:
        raise HTTPException(404, "Style not found")

    if not row:
        raise HTTPException(404, "Style not found")

    return dict(row)


def _generate_custom_brief(image_paths: list[str], name: str, description: str) -> str:
    """Call Gemini Vision to generate a style brief from uploaded images.
    Falls back to the user's description if Gemini is unavailable."""
    try:
        import httpx

        from cli import config as cfg
        from generators import gcp_auth

        model = cfg.get("gemini.vision_model", "gemini-2.5-pro")
        url = gcp_auth.vertex_url(model)

        parts: list[dict] = []
        for p in image_paths[:5]:
            path = Path(p)
            if path.exists():
                mime = mimetypes.guess_type(str(path))[0] or "image/jpeg"
                parts.append({
                    "inlineData": {
                        "data": base64.b64encode(path.read_bytes()).decode(),
                        "mimeType": mime,
                    }
                })

        prompt = (
            f"You are a visual style analyst. The user has named this style '{name}'.\n"
            f"User description: {description or 'None provided'}\n\n"
            "Analyse the attached reference images and write a STYLE BRIEF (200-300 words) "
            "for a generative image model. Focus on: color palette (exact hex codes), "
            "lighting, rendering technique, mood, and any recurring visual signatures. "
            "Write as directives: 'Use...', 'Apply...', 'Render...'"
        )
        parts.append({"text": prompt})

        with httpx.Client(timeout=90.0) as c:
            resp = c.post(
                url,
                json={
                    "contents": [{"role": "user", "parts": parts}],
                    "generationConfig": {"responseModalities": ["TEXT"]},
                },
                headers=gcp_auth.auth_headers(),
            )

        if resp.status_code >= 300:
            return description or f"Custom style: {name}"

        texts = []
        for cand in resp.json().get("candidates", []):
            for part in (cand.get("content") or {}).get("parts", []):
                if "text" in part:
                    texts.append(part["text"])

        return "\n".join(texts).strip() or (description or f"Custom style: {name}")
    except Exception:
        return description or f"Custom style: {name}"


def _generate_prompt_prefix(image_paths: list[str], name: str, description: str) -> str:
    """Generate a short one-line image_prompt_prefix from the style images."""
    try:
        import httpx

        from cli import config as cfg
        from generators import gcp_auth

        model = cfg.get("gemini.vision_model", "gemini-2.5-pro")
        url = gcp_auth.vertex_url(model)

        parts: list[dict] = []
        for p in image_paths[:3]:
            path = Path(p)
            if path.exists():
                mime = mimetypes.guess_type(str(path))[0] or "image/jpeg"
                parts.append({
                    "inlineData": {
                        "data": base64.b64encode(path.read_bytes()).decode(),
                        "mimeType": mime,
                    }
                })

        parts.append({
            "text": (
                "Write a single compact image generation style prefix (one sentence, max 30 words) "
                "that captures the rendering technique, aesthetic, and mood of these reference images. "
                "No subject matter. Output only the prefix text, no preamble."
            )
        })

        with httpx.Client(timeout=60.0) as c:
            resp = c.post(
                url,
                json={
                    "contents": [{"role": "user", "parts": parts}],
                    "generationConfig": {"responseModalities": ["TEXT"]},
                },
                headers=gcp_auth.auth_headers(),
            )

        if resp.status_code >= 300:
            return f"{name} style."

        texts = []
        for cand in resp.json().get("candidates", []):
            for part in (cand.get("content") or {}).get("parts", []):
                if "text" in part:
                    texts.append(part["text"])

        return "\n".join(texts).strip() or f"{name} style."
    except Exception:
        return f"{name} style."
