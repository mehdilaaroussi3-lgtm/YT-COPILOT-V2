"""Script-to-clickable-moment extractor (masterplan §9.3)."""
from __future__ import annotations

from generators.gemini_text import generate_text


SCRIPT_PROMPT = """\
VIDEO TITLE: "{title}"
FULL SCRIPT:
{script}

Find the SINGLE most visually compelling moment in this script that would make
the best YouTube thumbnail. Return STRICT JSON only:

{{
  "moment": "the exact line or paragraph from the script (quote it)",
  "why": "why this moment is the most clickable",
  "visual_concept": "1-2 sentence description of the thumbnail visual",
  "text_hook": "3-5 word UPPERCASE text overlay candidate"
}}
"""


def extract_clickable_moment(title: str, script: str) -> dict:
    raw = generate_text(
        SCRIPT_PROMPT.format(title=title, script=script[:8000]),
        temperature=0.4,
    )
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:]
    import json, re
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        return json.loads(m.group(0)) if m else {}
