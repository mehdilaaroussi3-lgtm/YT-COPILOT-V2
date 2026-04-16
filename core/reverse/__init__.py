"""Ultimate Reverse Engineer (URE).

Picture-perfect YouTube video dissection: scenes, keyframes, motion
analysis, Gemini Vision labels, transcript, audio formula, and a
production blueprint ready to drive a future generation pipeline.

Vision stays on Gemini; text reasoning routes through the Claude CLI
(see CLAUDE.md hard rules). URE is isolated from all existing tools
(thumbnail, ideas, titles, studio) — it imports only the Claude text
router and the shared DB.
"""
from __future__ import annotations

from core.reverse.pipeline import reverse

__all__ = ["reverse"]
