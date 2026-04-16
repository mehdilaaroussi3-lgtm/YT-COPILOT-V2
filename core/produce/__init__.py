"""Production Pipeline — assembles a finished MP4 from a URE blueprint.

VO audio drives all timing: each frame stays on screen for exactly the
duration its TTS clip takes to speak. Zero fixed durations, zero drift.

Vision (images) → Gemini. Text (script) → Claude router. TTS → ElevenLabs.
Video rendering → FFmpeg (bundled via imageio-ffmpeg).

Isolated from all existing tools.
"""
from __future__ import annotations

from core.produce.pipeline import produce

__all__ = ["produce"]
