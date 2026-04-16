"""Stage 10: extract script/VO formula via the Claude text router.

Hard rule (CLAUDE.md): all text reasoning routes through
generators.gemini_text.generate_text, which dispatches to the local Claude
CLI by default. Never call Gemini for text here.
"""
from __future__ import annotations

import json
import re

from generators.gemini_text import generate_text


PROMPT = """\
You are reverse-engineering the SCRIPT formula of a YouTube video from its
full transcript. Return ONLY valid JSON — no prose, no fences.

Transcript (with timestamps):
{transcript}

Analyze and return:
{{
  "hook_pattern": "short label e.g. 'question + stakes', 'shock statement', 'list promise', 'story cold-open'",
  "hook_text": "the actual hook words from the first 15 seconds",
  "hook_window_s": [0, 12],
  "narrative_arc": ["setup", "escalation", "twist", "payoff"],
  "arc_beats": [
    {{"beat": "setup", "start_s": 0, "end_s": 45, "summary": "..."}},
    ...
  ],
  "information_revelation_pattern": {{
    "strategy": "one of: breadcrumb|pyramid|mystery_box|contrast_reveal|chronological|problem_solution",
    "description": "one sentence — exactly how information is withheld and released to maintain tension (e.g. 'Stakes revealed upfront, mechanism withheld until 60%, solution drip-fed in final third')",
    "tension_peak_s": 0,
    "key_withholding_techniques": ["technique1", "technique2"]
  }},
  "sentence_rhythm": {{"avg_words": 11, "stdev": 4}},
  "tone": ["authoritative", "curious"],
  "vo_style": "one sentence on narration style (energy, pacing, music-duck behavior)",
  "call_to_action": "the final CTA text, or null",
  "reproducibility_notes": "what makes this script's formula repeatable for a new topic"
}}
"""


def _strip_fence(s: str) -> str:
    s = s.strip()
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z]*\n?", "", s)
        s = re.sub(r"\n?```$", "", s)
    return s.strip()


def _format_transcript(segments: list[dict], max_chars: int = 18000) -> str:
    lines: list[str] = []
    total = 0
    for s in segments:
        line = f"[{s['start']:.1f}] {s['text']}"
        total += len(line) + 1
        if total > max_chars:
            lines.append("[... truncated ...]")
            break
        lines.append(line)
    return "\n".join(lines)


def extract(transcript_segments: list[dict]) -> dict:
    if not transcript_segments:
        return {}
    prompt = PROMPT.format(transcript=_format_transcript(transcript_segments))
    try:
        raw = generate_text(prompt, temperature=0.2)
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)}
    raw = _strip_fence(raw)
    try:
        return json.loads(raw)
    except Exception:  # noqa: BLE001
        return {"raw": raw}
