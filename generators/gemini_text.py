"""Text generation router.

Historical name. All text reasoning now routes through the local Claude CLI
via generators/claude_text.py. The Gemini text path is retained behind
`text.engine: "gemini"` in config.yml as an escape hatch only.

Vision and image generation continue to use the Gemini API directly — this
module is text-only. See CLAUDE.md at the repo root for the rule.
"""
from __future__ import annotations

import random
import time

import httpx

from cli import config as cfg
from generators import gcp_auth


class TextError(RuntimeError):
    pass


def generate_text(prompt: str, model: str | None = None,
                   temperature: float = 0.4) -> str:
    """Route text generation to the configured engine (default: claude)."""
    engine = (cfg.get("text.engine") or "claude").lower()
    if engine == "claude":
        from generators.claude_text import generate_text as _claude_generate
        from generators.claude_text import ClaudeTextError
        try:
            return _claude_generate(prompt, model=model, temperature=temperature)
        except ClaudeTextError as e:
            raise TextError(str(e)) from e
    return _generate_text_gemini(prompt, model=model, temperature=temperature)


def _generate_text_gemini(prompt: str, model: str | None = None,
                           temperature: float = 0.4) -> str:
    """Legacy Gemini text path. Only reached when text.engine == 'gemini'."""
    model = model or cfg.get("gemini.vision_model", "gemini-2.5-pro")
    url = gcp_auth.vertex_url(model)

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
                resp = c.post(url, json=body, headers=gcp_auth.auth_headers())
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
