"""Thumbnail Style Agent (masterplan §25.3).

Build a structured style index of cached thumbnails using Gemini Vision.
Enables 'find similar' lookups via tag overlap.
"""
from __future__ import annotations

import base64
import datetime as dt
import json
import random
import time
from pathlib import Path

import httpx

from cli import config as cfg
from generators import gcp_auth
from data.db import db

DESCRIBE_PROMPT = """\
Analyze this YouTube thumbnail. Return STRICT JSON with these keys:

{
  "subject": "what the main visual element is, in 5-10 words",
  "composition": "center / left_third / right_third / split / full_frame",
  "text_amount": "none / minimal (1-3 words) / moderate (4-7) / heavy (8+)",
  "text_position": "upper_third / lower_third / center / none",
  "lighting": "dramatic / flat / rim / cinematic / natural",
  "mood": "tense / urgent / curious / playful / serious / mysterious",
  "color_temperature": "warm / cool / mixed / neutral",
  "dominant_colors": ["#hex1", "#hex2", "#hex3"],
  "brightness": "dark / medium / bright",
  "style_tags": ["tag1", "tag2", "tag3", "tag4", "tag5"]
}

Output ONLY the JSON object. No prose, no markdown fence.
"""


class ThumbnailStyleAgent:
    def __init__(self) -> None:
        self.db = db()
        self.model = cfg.get("gemini.vision_model", "gemini-2.5-pro")
        self.url = gcp_auth.vertex_url(self.model)

    def _vision_call(self, image_bytes: bytes) -> dict:
        body = {
            "contents": [{"role": "user", "parts": [
                {"inlineData": {"data": base64.b64encode(image_bytes).decode(),
                                "mimeType": "image/jpeg"}},
                {"text": DESCRIBE_PROMPT},
            ]}],
            "generationConfig": {"responseModalities": ["TEXT"]},
        }
        for attempt in range(4):
            try:
                with httpx.Client(timeout=120.0) as c:
                    resp = c.post(self.url, json=body,
                                  headers=gcp_auth.auth_headers())
                if resp.status_code == 429:
                    pass
                elif resp.status_code >= 300:
                    raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:300]}")
                else:
                    payload = resp.json()
                    text = ""
                    for cand in payload.get("candidates", []):
                        for part in (cand.get("content") or {}).get("parts", []):
                            if "text" in part:
                                text += part["text"]
                    text = text.strip()
                    # Strip markdown fences if present
                    if text.startswith("```"):
                        text = text.strip("`").lstrip("json").strip()
                    return json.loads(text)
            except Exception:
                pass
            time.sleep(min(5 * (2 ** attempt), 60) * (0.5 + random.random() * 0.5))
        return {}

    def describe(self, image_path: Path) -> dict:
        return self._vision_call(image_path.read_bytes())

    def index_video(self, video_id: str, image_path: Path) -> dict:
        desc = self.describe(image_path)
        if not desc:
            return {}
        self.db["thumbnails"].upsert({
            "video_id": video_id,
            "file_path": str(image_path),
            "description": desc.get("subject", ""),
            "style_tags": ",".join(desc.get("style_tags", [])),
            "colors": json.dumps(desc.get("dominant_colors", [])),
            "text_amount": desc.get("text_amount", ""),
            "analyzed_at": dt.datetime.now(dt.UTC).isoformat(),
        }, pk="video_id", alter=True)
        return desc

    def find_similar(self, query_tags: list[str], limit: int = 10) -> list[dict]:
        """Return cached thumbnails ranked by tag overlap."""
        rows = list(self.db["thumbnails"].rows_where(
            "style_tags IS NOT NULL AND style_tags != ''"
        ))
        scored = []
        qset = {t.lower() for t in query_tags}
        for r in rows:
            tags = {t.strip().lower() for t in (r.get("style_tags") or "").split(",")}
            overlap = len(qset & tags)
            if overlap > 0:
                scored.append((overlap, r))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [r for _, r in scored[:limit]]
