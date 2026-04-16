"""Read a user sketch and distill it into a clean composition description.

Gemini's image model is bad at reading bitmap sketches literally — it tends
to fold the sketch into whatever the reference images suggest. Pre-describing
the sketch as TEXT lets the generation prompt assert spatial intent
explicitly, bypassing that fusion.

The reader is also aggressive about ignoring faded/scribbled marks: users
sometimes leave light-grey doodles on the canvas that shouldn't become
subjects in the final render.
"""
from __future__ import annotations

import base64
from pathlib import Path

import httpx

from cli import config as cfg
from generators import gcp_auth


SKETCH_READER_PROMPT = """\
You are reading a hand-drawn LAYOUT SKETCH for a YouTube thumbnail.

Your ONLY job is to describe the composition as text so another model can
render it faithfully. You are NOT designing the thumbnail. You are NOT
fixing the drawing. You are transcribing the spatial intent.

CRITICAL READING RULES:
1. Only BOLD, CLEARLY-COLORED strokes count as composition. Ignore faded,
   light-grey, half-erased, or scribbled marks — those are noise from the
   user's drawing process, NOT intentional content. If something looks like
   a scratched-out label, ignore it completely.
2. Do NOT invent subjects the sketch doesn't actually show. If the sketch
   is a pyramid on a horizon, say "pyramid on a horizon" — not "pyramid on
   a high-tech server" and not "pyramid with lightning".
3. Describe in PLAIN nouns. Don't use adjectives about mood, style, or
   aesthetic. Another model handles the style.
4. Name: the MAIN SUBJECT, WHERE it sits (top/center/left/right, ground/sky),
   what's BELOW it (ground, water, empty space), what's BESIDE it if
   anything, and how much empty space is where.

Output 2-4 short sentences, plain English. No preamble, no labels, no JSON.

Example outputs:
- "A tall triangular pyramid sits in the upper-center of the frame on a
   flat horizon line. The ground extends across the full width. The sky
   above is empty. The bottom half of the frame below the horizon is
   empty space."
- "A person's head-and-shoulders portrait occupies the left half of the
   frame. The right half is mostly empty. A small rectangular label sits
   near the portrait's ear on the right side."
- "Two triangular shapes face each other in the center of the frame like
   opposing arrows. The area around them is empty. No ground line drawn."
"""


def describe_sketch(sketch_path: Path) -> str:
    """Return a concise composition description of the sketch.

    Empty string on any failure — caller falls back to feeding the raw
    sketch bitmap to the image model without a description.
    """
    if sketch_path is None or not Path(sketch_path).exists():
        return ""
    try:
        model = cfg.get("gemini.vision_model", "gemini-2.5-pro")
        url = gcp_auth.vertex_url(model)
    except Exception:  # noqa: BLE001
        return ""

    parts = [
        {"inlineData": {
            "data": base64.b64encode(Path(sketch_path).read_bytes()).decode(),
            "mimeType": "image/png",
        }},
        {"text": SKETCH_READER_PROMPT},
    ]
    try:
        with httpx.Client(timeout=60.0) as c:
            resp = c.post(url, json={
                "contents": [{"role": "user", "parts": parts}],
                "generationConfig": {
                    "responseModalities": ["TEXT"],
                    "temperature": 0.15,
                },
            }, headers=gcp_auth.auth_headers())
        if resp.status_code >= 300:
            return ""
        payload = resp.json()
        texts: list[str] = []
        for cand in payload.get("candidates", []):
            for p in (cand.get("content") or {}).get("parts", []):
                if "text" in p:
                    texts.append(p["text"])
        return "\n".join(texts).strip()
    except Exception:  # noqa: BLE001
        return ""
