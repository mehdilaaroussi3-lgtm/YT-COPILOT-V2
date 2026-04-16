"""Quality gate (masterplan §21). Vision describes the result, simple heuristic scores it."""
from __future__ import annotations

import base64
from pathlib import Path

import httpx

from cli import config as cfg
from generators import gcp_auth

DESCRIBE_PROMPT = """\
Describe this YouTube thumbnail in 60-100 words:
- Main subject and its placement
- Dominant colors and brightness
- Is there text? Is it readable?
- Lighting style
- Does it look AI-generated or human-designed?
- What emotion does it convey?
- Any obvious flaws (distorted hands, garbled text, plastic textures, generic lighting)?
"""


def describe(image_path: Path) -> str:
    model = cfg.get("gemini.vision_model", "gemini-2.5-pro")
    url = gcp_auth.vertex_url(model)
    body = {
        "contents": [{"role": "user", "parts": [
            {"inlineData": {"data": base64.b64encode(image_path.read_bytes()).decode(),
                            "mimeType": "image/png"}},
            {"text": DESCRIBE_PROMPT},
        ]}],
        "generationConfig": {"responseModalities": ["TEXT"]},
    }
    with httpx.Client(timeout=120.0) as c:
        resp = c.post(url, json=body, headers=gcp_auth.auth_headers())
    resp.raise_for_status()
    payload = resp.json()
    out = []
    for cand in payload.get("candidates", []):
        for part in (cand.get("content") or {}).get("parts", []):
            if "text" in part:
                out.append(part["text"])
    return "\n".join(out).strip()


def heuristic_score(description: str) -> tuple[float, list[str]]:
    """Quick lexical score from a Vision description. 0-10."""
    d = description.lower()
    score = 7.0
    issues = []
    BAD = ["plastic", "ai-generated", "garbled", "distorted", "generic", "stock photo",
           "flat lighting", "lifeless", "unreadable", "blurry", "smeared",
           "extra finger", "too many fingers", "deformed"]
    GOOD = ["dramatic", "high contrast", "cinematic", "editorial", "professional",
            "human-designed", "crisp", "readable", "moody", "striking"]
    for w in BAD:
        if w in d:
            score -= 1.2
            issues.append(f"flag: {w}")
    for w in GOOD:
        if w in d:
            score += 0.5
    return max(0.0, min(10.0, score)), issues
