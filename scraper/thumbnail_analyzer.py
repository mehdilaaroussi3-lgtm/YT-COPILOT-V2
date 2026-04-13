"""Use Gemini Vision to analyze cached reference thumbnails and produce a style brief.

Uses the same Vertex API-key endpoint as the image generator — no SDK, no OAuth.
"""
from __future__ import annotations

import base64
import random
import time
from pathlib import Path

import httpx

from cli import config as cfg


VERTEX_HOST = "https://aiplatform.googleapis.com"
ENDPOINT_TMPL = "/v1/publishers/google/models/{model}:generateContent"


ANALYSIS_PROMPT = """\
You are a YouTube thumbnail expert for {niche} content.
I'm showing you {count} thumbnails from TOP PERFORMING videos in this niche
(massive view counts, 5x+ outliers vs their channel average).

Extract the COMMON PATTERNS across these thumbnails:

1. COLOR PALETTE: Exact dominant colors (with hex codes), background vs
   foreground contrast.
2. COMPOSITION: Focal point position (center / left third / right third),
   how much of the frame is filled by the subject, rule-of-thirds usage.
3. TEXT USAGE: Word count, font weight/style, position (upper third? lower?),
   color, outlines/strokes.
4. LIGHTING: Direction (rim / front / side), dramatic vs flat, color
   temperature (warm / cool / mixed).
5. MOOD: What emotion do they convey? How do they create curiosity?
6. VISUAL ELEMENTS: Recurring props, icons, overlays, borders, textures.
7. WHAT THEY AVOID: What do these thumbnails NOT do?

Output a concise, specific STYLE BRIEF (under 400 words) usable as design
instructions for a generative model. Be concrete, not vague — name colors,
positions, and techniques explicitly.
"""


class VisionError(RuntimeError):
    pass


def analyze_thumbnails(thumbnail_paths: list[Path], niche: str,
                        max_refs: int = 8) -> str:
    """Send up to N thumbnails to Gemini Vision and return a style brief."""
    paths = thumbnail_paths[:max_refs]
    if not paths:
        return "(no reference thumbnails available)"

    api_key = cfg.get("vertex.api_key")
    if not api_key or api_key.startswith("your-"):
        raise VisionError("vertex.api_key not set in config.yml")

    vision_model = cfg.get("gemini.vision_model", "gemini-2.5-pro")
    url = f"{VERTEX_HOST}{ENDPOINT_TMPL.format(model=vision_model)}?key={api_key}"

    parts: list[dict] = []
    for p in paths:
        data = Path(p).read_bytes()
        parts.append({
            "inlineData": {
                "data": base64.b64encode(data).decode(),
                "mimeType": "image/jpeg",
            }
        })
    parts.append({"text": ANALYSIS_PROMPT.format(niche=niche, count=len(paths))})

    body = {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {"responseModalities": ["TEXT"]},
    }

    last_err: str | None = None
    for attempt in range(6):
        try:
            with httpx.Client(timeout=120.0) as client:
                resp = client.post(
                    url, json=body,
                    headers={"Content-Type": "application/json"},
                )
            if resp.status_code == 429:
                last_err = f"429: {resp.text[:200]}"
            elif resp.status_code >= 300:
                raise VisionError(f"HTTP {resp.status_code}: {resp.text[:500]}")
            else:
                payload = resp.json()
                texts: list[str] = []
                for cand in payload.get("candidates", []):
                    for part in (cand.get("content") or {}).get("parts", []):
                        if "text" in part:
                            texts.append(part["text"])
                out = "\n".join(texts).strip()
                if out:
                    return out
                last_err = "empty response"
        except (httpx.TimeoutException, httpx.NetworkError) as e:
            last_err = f"{type(e).__name__}: {e}"

        delay = min(5000 * (2 ** attempt), 120000) * (0.5 + random.random() * 0.5) / 1000.0
        print(f"  [vision retry {attempt + 1}/6] {last_err} — sleeping {delay:.1f}s")
        time.sleep(delay)

    raise VisionError(f"Vision analysis failed: {last_err}")
