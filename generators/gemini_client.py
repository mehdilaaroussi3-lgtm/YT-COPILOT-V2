"""YTC 3.0 Pro Image client — Vertex AI API-key endpoint (no SDK, no OAuth).

Uses the global aiplatform.googleapis.com host which auto-routes to the region
with most capacity. Mandatory exponential-backoff-with-jitter retry for 429s.
"""
from __future__ import annotations

import base64
import random
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import httpx

from cli import config as cfg
from generators import gcp_auth

MIME_BY_EXT = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".avif": "image/avif",
}
EXT_BY_MIME = {v: k for k, v in MIME_BY_EXT.items()}


class GeminiError(RuntimeError):
    pass


class GeminiSafetyRefusal(GeminiError):
    """Model returned only text (refusal/safety) — retryable per spec."""


@dataclass
class GeminiImage:
    """Result of a generation call."""
    data: bytes
    mime_type: str
    text: str = ""

    @property
    def extension(self) -> str:
        return EXT_BY_MIME.get(self.mime_type, ".png")


@dataclass
class GeminiImageClient:
    model: str = "gemini-3-pro-image-preview"
    image_size: str = "2K"
    aspect_ratio: str = "16:9"
    timeout_seconds: float = 120.0
    max_attempts: int = 6
    base_backoff_ms: int = 5000
    max_backoff_ms: int = 120000

    @classmethod
    def from_config(cls) -> "GeminiImageClient":
        return cls(
            model=cfg.get("gemini.image_model", "gemini-3-pro-image-preview"),
            image_size=cfg.get("gemini.image_size", "2K"),
            aspect_ratio=cfg.get("gemini.aspect_ratio", "16:9"),
        )

    def _url(self) -> str:
        return gcp_auth.vertex_url(self.model)

    def _build_body(self, prompt: str, reference_images: list[Path]) -> dict:
        parts: list[dict] = []
        # Reference images BEFORE the text part. Max 2 reliable per spec.
        for img_path in reference_images[:2]:
            p = Path(img_path)
            mime = MIME_BY_EXT.get(p.suffix.lower(), "image/png")
            parts.append({
                "inlineData": {
                    "data": base64.b64encode(p.read_bytes()).decode(),
                    "mimeType": mime,
                }
            })
        parts.append({"text": prompt})

        return {
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {
                "responseModalities": ["IMAGE", "TEXT"],
                "imageConfig": {
                    "imageSize": self.image_size,
                    "aspectRatio": self.aspect_ratio,
                },
            },
        }

    def _backoff_delay(self, attempt: int) -> float:
        """Exponential with jitter: min(5s * 2^a, 120s) * (0.5 + rand*0.5)."""
        cap_ms = min(self.base_backoff_ms * (2 ** attempt), self.max_backoff_ms)
        jitter = 0.5 + random.random() * 0.5
        return (cap_ms * jitter) / 1000.0

    def generate(
        self,
        prompt: str,
        reference_images: Iterable[Path] | None = None,
    ) -> GeminiImage:
        """Generate one image. Retries 429s + transient failures up to 6 times."""
        refs = list(reference_images or [])
        body = self._build_body(prompt, refs)
        url = self._url()

        last_err: str | None = None
        for attempt in range(self.max_attempts):
            try:
                with httpx.Client(timeout=self.timeout_seconds) as client:
                    resp = client.post(
                        url,
                        json=body,
                        headers=gcp_auth.auth_headers(),
                    )

                # Retryable HTTP statuses
                if resp.status_code == 429:
                    last_err = f"429 rate-limited: {resp.text[:200]}"
                    self._sleep(attempt, last_err)
                    continue

                # Non-retryable error
                if resp.status_code < 200 or resp.status_code >= 300:
                    raise GeminiError(
                        f"HTTP {resp.status_code}: {resp.text[:500]}"
                    )

                # Parse response
                try:
                    parsed = _parse_response(resp.json())
                    try:
                        from core.session_stats import increment
                        increment("image")
                    except Exception:  # noqa: BLE001
                        pass
                    return parsed
                except GeminiSafetyRefusal as e:
                    last_err = f"safety/text-only response: {e}"
                    self._sleep(attempt, last_err)
                    continue
                except GeminiError as e:
                    # Missing parts / inlineData → retryable per spec
                    last_err = str(e)
                    self._sleep(attempt, last_err)
                    continue

            except (httpx.TimeoutException, httpx.NetworkError) as e:
                last_err = f"{type(e).__name__}: {e}"
                self._sleep(attempt, last_err)
                continue

        raise GeminiError(
            f"Generation failed after {self.max_attempts} attempts. Last error: {last_err}"
        )

    def _sleep(self, attempt: int, reason: str) -> None:
        if attempt + 1 >= self.max_attempts:
            return
        delay = self._backoff_delay(attempt)
        # Caller can wrap in rich console; print is fine here.
        print(f"  [retry {attempt + 1}/{self.max_attempts}] {reason} — sleeping {delay:.1f}s")
        time.sleep(delay)


def _parse_response(payload: dict) -> GeminiImage:
    candidates = payload.get("candidates") or []
    if not candidates:
        raise GeminiError(f"No candidates in response: {str(payload)[:300]}")

    parts = (candidates[0].get("content") or {}).get("parts") or []
    if not parts:
        import json
        print(f"[DEBUG] Full Gemini response: {json.dumps(payload, indent=2)[:1500]}")
        raise GeminiError("Candidate has no parts")

    text_chunks = []
    for p in parts:
        inline = p.get("inlineData") or p.get("inline_data")
        if inline and inline.get("data"):
            mime = inline.get("mimeType") or inline.get("mime_type") or "image/png"
            return GeminiImage(
                data=base64.b64decode(inline["data"]),
                mime_type=mime,
                text="\n".join(text_chunks),
            )
        if "text" in p:
            text_chunks.append(p["text"])

    # Only text returned — refusal/safety. Caller should treat as retryable.
    raise GeminiSafetyRefusal(
        "Response contained only text, no inlineData. "
        f"Text: {' '.join(text_chunks)[:300]}"
    )
