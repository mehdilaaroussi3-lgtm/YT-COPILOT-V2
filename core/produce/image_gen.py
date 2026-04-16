"""Stage 3a: per-scene image generation via Gemini."""
from __future__ import annotations

from pathlib import Path

from generators.gemini_client import GeminiImageClient


def render(image_prompt: str, out_path: Path, force: bool = False,
           style_id: str | None = None) -> Path:
    """Generate a still image from the prompt and save as PNG.

    If style_id is provided, resolves style and prepends image_prompt_prefix
    to the prompt, and passes reference images to Gemini.
    """
    if not force and out_path.exists():
        return out_path

    refs: list[Path] = []
    if style_id:
        from core.style_resolver import resolve_style
        try:
            sr = resolve_style(style_id)
            if sr.image_prompt_prefix:
                image_prompt = sr.image_prompt_prefix + "\n\n" + image_prompt
            refs = sr.reference_images[:2]
        except Exception:
            pass  # graceful degradation

    client = GeminiImageClient.from_config()
    result = client.generate(image_prompt, reference_images=refs if refs else None)
    out_path.write_bytes(result.data)
    return out_path
