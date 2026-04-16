"""Stage 6: Gemini Vision labeling per scene (2-frame input).

Mirrors the inlineData pattern from core/channel_text_dna.py. Vision stays
on Gemini per the CLAUDE.md hard rule — never route image analysis through
Claude.
"""
from __future__ import annotations

import base64
import json
import random
import re
import time
from pathlib import Path

import httpx

from cli import config as cfg
from generators import gcp_auth

PROMPT = """\
You are analyzing ONE scene from a YouTube video. I'm showing you TWO frames
from that scene: frame A is the mid-scene keyframe, frame B is sampled ~1
second later. Compare them to judge both content and motion.

Return ONLY valid JSON with this exact shape:
{
  "shot_type": "close_up|medium|wide|extreme_close_up|over_shoulder|pov|overhead|graphic|text_card|montage|other",
  "production_type": "live_action|ai_image_static|ai_image_animated|stock_footage|motion_graphic|screen_recording|mixed",
  "production_evidence": "one sentence on what in the frames led to the production_type call",
  "rendering_pipeline": "ai_generated_image|real_camera|vector_animation|3d_render|hand_drawn|screen_capture|composite",
  "art_direction": "one sentence on HOW this frame is rendered — lighting treatment, color grade, texture quality, rendering style — NOT what subject is shown. E.g. 'High-contrast cinematic grade with warm amber key light and deep shadow falloff' or 'Flat vector illustration with bold outlines and solid fill colors'",
  "has_face": true|false,
  "face_count": 0,
  "description": "one or two sentences describing what's in the scene",
  "on_screen_text": "exact text visible on screen, or empty string",
  "dominant_colors": ["#RRGGBB", "#RRGGBB", "#RRGGBB"],
  "motion_type": "static|camera_pan|camera_zoom|ken_burns|internal_motion|talking_head|cut|unknown",
  "style_tags": ["tag1", "tag2", "tag3"]
}

Production-type guidance:
- ai_image_animated: still image with added motion (warped backgrounds,
  morphing edges, parallax anomalies, unnatural fluid motion)
- ai_image_static: clearly AI-generated still with no real motion (Ken Burns
  zoom/pan of a generated image counts as ai_image_static if content is AI)
- live_action: real camera footage of real people/places
- stock_footage: curated real footage that's generic/cinematic, not
  protagonist-driven
- motion_graphic: vector/text/data-viz animation
- screen_recording: UI, desktop, phone, gameplay capture

rendering_pipeline guidance:
- ai_generated_image: photorealistic or stylized image made by diffusion/LLM model
- real_camera: genuine camera capture (live action, stock, documentary)
- vector_animation: flat 2D vector art, motion graphics, SVG-style
- 3d_render: CGI, 3D modeled scene, game engine footage
- hand_drawn: illustrations, sketches, watercolor, painted frames
- screen_capture: UI recording, desktop, mobile app, gameplay
- composite: mix of real footage with CG overlays, VFX, keyed elements

CRITICAL — art_direction must describe the RENDERING STYLE only:
  CORRECT: "Desaturated cinematic grade, shallow depth of field, film grain, high-contrast shadows"
  CORRECT: "Flat 2D vector style, bold outlines, saturated solid fills, minimal shading"
  WRONG: "Shows a pilot in a cockpit" (that's description, not art direction)
  WRONG: "Minimalist icon of a plane" (that describes subject matter)

No prose outside the JSON. No markdown fences.
"""


def _strip_fence(s: str) -> str:
    s = s.strip()
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z]*\n?", "", s)
        s = re.sub(r"\n?```$", "", s)
    return s.strip()


BATCH_PROMPT = """\
I am showing you {n} keyframes, one from each scene of a YouTube video.
They are provided in scene order. Analyse every frame and return a JSON
array of exactly {n} objects — one per frame, in the same order.

Each object must have this exact shape:
{{
  "shot_type": "close_up|medium|wide|extreme_close_up|over_shoulder|pov|overhead|graphic|text_card|montage|other",
  "production_type": "live_action|ai_image_static|ai_image_animated|stock_footage|motion_graphic|screen_recording|mixed",
  "production_evidence": "one sentence",
  "rendering_pipeline": "ai_generated_image|real_camera|vector_animation|3d_render|hand_drawn|screen_capture|composite",
  "art_direction": "one sentence on HOW this frame is rendered — lighting, color grade, texture, rendering method — NOT what is shown",
  "has_face": true|false,
  "face_count": 0,
  "description": "one or two sentences",
  "on_screen_text": "exact text or empty string",
  "dominant_colors": ["#RRGGBB", "#RRGGBB", "#RRGGBB"],
  "motion_type": "static|camera_pan|camera_zoom|ken_burns|internal_motion|talking_head|cut|unknown",
  "style_tags": ["tag1", "tag2"]
}}

Production-type guidance:
- ai_image_animated: still AI image with added motion (warped bg, parallax)
- ai_image_static: AI-generated still / Ken Burns of AI content
- live_action: real camera footage
- stock_footage: generic curated real footage
- motion_graphic: vector/text/data-viz animation
- screen_recording: UI, desktop, phone, gameplay

rendering_pipeline guidance:
- ai_generated_image: diffusion/LLM-made photorealistic or stylized image
- real_camera: genuine camera capture (live action, stock, documentary)
- vector_animation: flat 2D vector art, motion graphics, SVG-style
- 3d_render: CGI, modeled scene, game engine
- hand_drawn: illustrations, sketches, painted frames
- screen_capture: UI recording, desktop, mobile, gameplay
- composite: real footage + CG overlays, VFX

CRITICAL — art_direction describes RENDERING STYLE only, never subject matter:
  CORRECT: "Desaturated cinematic grade, shallow depth of field, film grain"
  CORRECT: "Flat 2D vector, bold outlines, saturated solid fills, minimal shading"
  WRONG: "Shows a man walking in a city" (subject matter, not rendering)

Return ONLY the JSON array. No prose, no fences, no extra keys.
"""


def label_scenes_batch(frames: list[Path], batch_size: int = 8) -> list[dict]:
    """Analyse multiple scene keyframes in batched Gemini Vision calls.

    Sends `batch_size` frames per API call instead of one call per scene.
    Falls back to empty dicts for any scene whose batch call fails.
    """
    try:
        model = cfg.get("gemini.vision_model", "gemini-2.5-pro")
        url = gcp_auth.vertex_url(model)
    except Exception:  # noqa: BLE001
        return [{} for _ in frames]

    results: list[dict] = []

    for i in range(0, len(frames), batch_size):
        batch = frames[i:i + batch_size]
        n = len(batch)
        parts: list[dict] = []
        for frame in batch:
            if frame.exists():
                parts.append({
                    "inlineData": {
                        "data": base64.b64encode(frame.read_bytes()).decode(),
                        "mimeType": "image/jpeg",
                    }
                })
            else:
                # placeholder 1×1 white JPEG so the index stays aligned
                parts.append({
                    "inlineData": {
                        "data": "/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/wAALCAABAAEBAREA/8QAFAABAAAAAAAAAAAAAAAAAAAACf/EABQQAQAAAAAAAAAAAAAAAAAAAAD/2gAIAQEAAT8AVf/Z",
                        "mimeType": "image/jpeg",
                    }
                })
        parts.append({"text": BATCH_PROMPT.format(n=n)})

        body = {
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {"responseModalities": ["TEXT"], "temperature": 0.1},
        }

        batch_results: list[dict] = [{} for _ in batch]
        last_err: str | None = None

        for attempt in range(6):
            try:
                with httpx.Client(timeout=120.0) as c:
                    resp = c.post(url, json=body,
                                  headers=gcp_auth.auth_headers())
                if resp.status_code == 429:
                    last_err = "429"
                elif resp.status_code >= 300:
                    break
                else:
                    texts: list[str] = []
                    for cand in resp.json().get("candidates", []):
                        for part in (cand.get("content") or {}).get("parts", []):
                            if "text" in part:
                                texts.append(part["text"])
                    raw = _strip_fence("\n".join(texts))
                    try:
                        parsed = json.loads(raw)
                        if isinstance(parsed, list):
                            for j, item in enumerate(parsed[:n]):
                                if isinstance(item, dict):
                                    batch_results[j] = item
                    except Exception:  # noqa: BLE001
                        pass
                    break
            except (httpx.TimeoutException, httpx.NetworkError) as e:
                last_err = type(e).__name__
            delay = min(5000 * (2 ** attempt), 60_000) * (0.5 + random.random() * 0.5) / 1000.0
            time.sleep(delay)

        results.extend(batch_results)

    return results


def label_scene(frame_a: Path, frame_b: Path) -> dict | None:
    """Call Gemini Vision on the frame pair. Returns parsed dict or None."""
    try:
        model = cfg.get("gemini.vision_model", "gemini-2.5-pro")
        url = gcp_auth.vertex_url(model)
    except Exception:  # noqa: BLE001
        return None

    parts = [
        {"inlineData": {"data": base64.b64encode(frame_a.read_bytes()).decode(),
                        "mimeType": "image/jpeg"}},
        {"inlineData": {"data": base64.b64encode(frame_b.read_bytes()).decode(),
                        "mimeType": "image/jpeg"}},
        {"text": PROMPT},
    ]
    body = {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {"responseModalities": ["TEXT"], "temperature": 0.2},
    }

    last_err: str | None = None
    for attempt in range(6):
        try:
            with httpx.Client(timeout=120.0) as c:
                resp = c.post(url, json=body, headers=gcp_auth.auth_headers())
            if resp.status_code == 429:
                last_err = "429"
            elif resp.status_code >= 300:
                return None
            else:
                payload = resp.json()
                texts: list[str] = []
                for cand in payload.get("candidates", []):
                    for part in (cand.get("content") or {}).get("parts", []):
                        if "text" in part:
                            texts.append(part["text"])
                raw = _strip_fence("\n".join(texts))
                try:
                    return json.loads(raw)
                except Exception:  # noqa: BLE001
                    return None
        except (httpx.TimeoutException, httpx.NetworkError) as e:
            last_err = type(e).__name__
        delay = min(5000 * (2 ** attempt), 60000) * (0.5 + random.random() * 0.5) / 1000.0
        time.sleep(delay)
    return None
