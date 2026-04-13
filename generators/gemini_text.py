"""Lightweight Gemini text-only client (used by agents for reasoning fallbacks).

When ThumbCraft runs inside Claude Code, Claude IS the reasoning engine and
this module is bypassed. When run standalone (CLI from a terminal), agents
call this for title pattern extraction, scoring, etc.
"""
from __future__ import annotations

import random
import time

import httpx

from cli import config as cfg

VERTEX_HOST = "https://aiplatform.googleapis.com"
ENDPOINT_TMPL = "/v1/publishers/google/models/{model}:generateContent"


class TextError(RuntimeError):
    pass


def generate_text(prompt: str, model: str | None = None,
                   temperature: float = 0.4) -> str:
    """One-shot text generation with retry."""
    api_key = cfg.get("vertex.api_key")
    if not api_key or api_key.startswith("your-"):
        raise TextError("vertex.api_key not set")
    model = model or cfg.get("gemini.vision_model", "gemini-2.5-pro")
    url = f"{VERTEX_HOST}{ENDPOINT_TMPL.format(model=model)}?key={api_key}"

    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseModalities": ["TEXT"],
            "temperature": temperature,
        },
    }

    last_err: str | None = None
    for attempt in range(6):
        try:
            with httpx.Client(timeout=120.0) as c:
                resp = c.post(url, json=body,
                              headers={"Content-Type": "application/json"})
            if resp.status_code == 429:
                last_err = "429"
            elif resp.status_code >= 300:
                raise TextError(f"HTTP {resp.status_code}: {resp.text[:400]}")
            else:
                payload = resp.json()
                texts: list[str] = []
                for cand in payload.get("candidates", []):
                    for part in (cand.get("content") or {}).get("parts", []):
                        if "text" in part:
                            texts.append(part["text"])
                out = "\n".join(texts).strip()
                if out:
                    try:
                        from core.session_stats import increment
                        increment("text")
                    except Exception:  # noqa: BLE001
                        pass
                    return out
                last_err = "empty"
        except (httpx.TimeoutException, httpx.NetworkError) as e:
            last_err = f"{type(e).__name__}"

        delay = min(5000 * (2 ** attempt), 120000) * (0.5 + random.random() * 0.5) / 1000.0
        print(f"  [text retry {attempt + 1}/6] {last_err} — sleep {delay:.1f}s")
        time.sleep(delay)

    raise TextError(f"Text generation failed: {last_err}")
