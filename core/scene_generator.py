"""Scene generator — produces 3 distinct visual concepts (literal, metaphor, bold).

Maps to the 3 generation variants. Uses Gemini text reasoning. When run inside
Claude Code, Claude IS the reasoning — but the standalone CLI hits Gemini text.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from generators.gemini_text import generate_text


SCENE_PROMPT = """\
VIDEO TITLE: "{title}"
NICHE: {niche}
{script_block}
{style_brief_block}

Generate EXACTLY 3 visual scene concepts for a YouTube thumbnail.
Concept 1 = LITERAL (most obvious interpretation)
Concept 2 = METAPHORICAL (symbolic interpretation)
Concept 3 = BOLD (unexpected, high-risk-high-reward)

For each concept, fill these fields (used to compose a 1of10-style prompt):

{{
  "subject": "main visual element (faceless: object/scene/symbol — NO human faces)",
  "subject_placement": "center | left_third | right_third",
  "background": "specific environment with named elements",
  "left_element": "what flanks the subject on the left",
  "right_element": "what flanks the subject on the right",
  "lighting": "direction + color temperature + mood (1 sentence)",
  "atmosphere": "fog/haze/particles/grain (1 sentence)",
  "brightest_point": "the single element that draws the eye first",
  "color_palette": ["#hex1", "#hex2", "#hex3"],
  "emotion": "what the viewer should feel",
  "curiosity_hook": "what visual element makes them NEED to click"
}}

Output STRICT JSON: a top-level array of 3 objects, in order [literal, metaphor, bold].
NO prose, NO markdown fence.
"""


@dataclass
class SceneConcept:
    subject: str
    subject_placement: str
    background: str
    left_element: str
    right_element: str
    lighting: str
    atmosphere: str
    brightest_point: str
    color_palette: list[str]
    emotion: str
    curiosity_hook: str
    kind: str   # "literal" | "metaphor" | "bold"

    @classmethod
    def from_dict(cls, d: dict, kind: str) -> "SceneConcept":
        return cls(
            subject=d.get("subject", ""),
            subject_placement=d.get("subject_placement", "center"),
            background=d.get("background", ""),
            left_element=d.get("left_element", ""),
            right_element=d.get("right_element", ""),
            lighting=d.get("lighting", ""),
            atmosphere=d.get("atmosphere", ""),
            brightest_point=d.get("brightest_point", ""),
            color_palette=d.get("color_palette", []) or [],
            emotion=d.get("emotion", ""),
            curiosity_hook=d.get("curiosity_hook", ""),
            kind=kind,
        )


def generate_scenes(
    title: str,
    niche: str,
    script_excerpt: str | None = None,
    style_brief: str | None = None,
) -> list[SceneConcept]:
    script_block = (
        f"SCRIPT EXCERPT:\n{script_excerpt[:2000]}\n" if script_excerpt else ""
    )
    style_block = f"STYLE BRIEF FROM TOP OUTLIERS:\n{style_brief}\n" if style_brief else ""

    prompt = SCENE_PROMPT.format(
        title=title, niche=niche,
        script_block=script_block,
        style_brief_block=style_block,
    )
    raw = generate_text(prompt, temperature=0.8)
    raw = _strip_fence(raw)
    try:
        items = json.loads(raw)
    except json.JSONDecodeError:
        # Try to find a JSON array inside the response
        m = re.search(r"\[.*\]", raw, re.DOTALL)
        if not m:
            raise
        items = json.loads(m.group(0))

    kinds = ["literal", "metaphor", "bold"]
    out = []
    for i, item in enumerate(items[:3]):
        out.append(SceneConcept.from_dict(item, kinds[i] if i < 3 else "literal"))
    return out


def _strip_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    return text.strip()
