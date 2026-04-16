"""Channel logo generator.

Downloads the reference channel's avatar, passes it to Gemini image gen
as a visual style reference, and produces a square PNG logo for the user's channel.
Same pipeline as thumbnails — vision reference drives the generation.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import httpx

LOGO_DIR = Path("data/channel_logos")
LOGO_ARCHIVE_DIR = Path("data/logos_archive")


def generate_logo(
    channel_name: str,
    niche: str,
    reference_channel_name: str,
    reference_avatar_url: str,
) -> Path:
    """Generate a 1:1 channel logo inspired by the reference channel's visual style.

    Returns the path to the saved logo PNG.
    """
    from generators.gemini_client import GeminiImageClient

    out_dir = LOGO_DIR / channel_name
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "logo.png"

    # ── Download reference avatar ────────────────────────────────────────────
    ref_path: Path | None = None
    if reference_avatar_url:
        try:
            resp = httpx.get(reference_avatar_url, timeout=15, follow_redirects=True)
            resp.raise_for_status()
            ref_path = out_dir / "ref_avatar.jpg"
            ref_path.write_bytes(resp.content)
        except Exception:
            ref_path = None

    # ── Build prompt ─────────────────────────────────────────────────────────
    ref_hint = f" visually inspired by {reference_channel_name}'s aesthetic" if reference_channel_name else ""
    prompt = (
        f"YouTube channel profile picture logo for a channel called '{channel_name}'{ref_hint}. "
        f"The channel topic: {niche}. "
        f"If a reference image is provided, absorb its color palette, visual energy, "
        f"and graphic language — then create a completely fresh, original identity. "
        f"Square 1:1 format. Bold, iconic, no text, no letters. "
        f"Clean professional YouTube channel avatar. Strong shapes, high contrast, memorable."
    )

    # ── Generate (1:1 square) ────────────────────────────────────────────────
    client = GeminiImageClient.from_config()
    client.aspect_ratio = "1:1"

    refs = [ref_path] if ref_path and ref_path.exists() else []
    result = client.generate(prompt, reference_images=refs)

    out_path.write_bytes(result.data)

    # ── Archive (permanent copy, survives channel deletion) ──────────────────
    LOGO_ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(out_path, LOGO_ARCHIVE_DIR / f"{channel_name}_logo.png")

    return out_path


def archive_existing_logo(channel_name: str) -> None:
    """Copy an already-generated logo to the archive (idempotent)."""
    src = LOGO_DIR / channel_name / "logo.png"
    if not src.exists():
        return
    LOGO_ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, LOGO_ARCHIVE_DIR / f"{channel_name}_logo.png")
