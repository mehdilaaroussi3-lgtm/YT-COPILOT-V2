"""Plan concrete visual concepts for a title in a channel's style.

Given: video title + per-channel style brief.
Returns: N distinct one-sentence visual concepts that describe WHAT the
thumbnail should show (specific subject, setting, mood) — not HOW it
should look (the channel's references handle the look).

This is the 'thinking' step between title and image. Without it, the image
model copies the reference's subjects too literally. With it, the image
model gets "a lone elderly Malaysian woman at a humid night market, warm
lanterns" — a concept grounded in the title — rendered in the channel's style.
"""
from __future__ import annotations

import json
import re

from generators.gemini_text import generate_text


PLANNER_PROMPT = """\
You are pitching {n} FUNDAMENTALLY DIFFERENT thumbnail concepts for ONE video.
Imagine {n} different creative directors competing for this brief — each
bringing a completely different angle. Your job is to generate all {n}.

VIDEO TITLE: "{title}"
CHANNEL: @{channel}
{brief_block}
Read the title carefully. What is the creator's STANCE? (critique, exposé,
warning, success, confession, doom, teaching, provocation) What is the
emotional truth of this video? Lock in the thesis before planning.

─── THE {n} CONCEPTS MUST BE RADICALLY DIFFERENT ───

Each concept must hit a different axis. Mix these axes across the {n}:

• FRAMING: intimate close-up  vs  wide editorial  vs  split-panel
  vs  symbolic / metaphorical object  vs  confrontation / face-off
• SUBJECT: a person  vs  an object  vs  a place  vs  a symbolic tableau
  vs  a before/after diptych
• MOMENT: the buildup  vs  the breaking point  vs  the aftermath
  vs  the decision  vs  the reveal
• EMOTIONAL ANGLE: fear  vs  absurdity  vs  regret  vs  defiance
  vs  quiet unease  vs  outrage
• LITERAL vs METAPHORICAL: sometimes show the actual thing (LinkedIn
  office), sometimes show a metaphor (a cage, a mask, a crumbling statue).

Do NOT generate {n} slight variations of the same idea. If concept 1 is
"a sad person at a desk," concept 2 should not be "a sad person on a
couch." Change the whole approach.

─── EACH CONCEPT MUST ALSO ───

- Be grounded in the title's thesis (not generic).
- Fit the CHANNEL'S ARTISTIC DIRECTION — feel natural next to their work.
  If the channel uses illustration, plan illustrations. If photography,
  plan photography. If editorial wides, plan editorial wides.
- Be ONE vivid sentence naming: the specific subject, the setting, the
  action/moment, the mood. Concrete nouns only — no generic adjectives.

Output STRICT JSON only — an array of {n} strings, no prose, no fence.

Example for title "LinkedIn is a horrible place" on a satirical channel,
showing 4 radically different angles:
["Tight head-and-shoulders crop of a hollow-eyed man in a suit, fake smile frozen, beige cubicle behind him, fluorescent dread",
 "Wide overhead shot of endless identical beige cubicles stretching to a vanishing point, one glowing laptop in the middle, cold corporate grey",
 "A cracked LinkedIn logo painted on a crumbling concrete wall, graffiti bleeding around it, gritty urban dusk light",
 "Split-panel: left side a stiff smiling corporate headshot, right side the same man screaming alone in a dark bathroom mirror"]
"""


def plan_concepts(title: str, channel: str, style_brief: str | None,
                    n: int = 4) -> list[str]:
    """Return N visual concepts. Falls back to [title] * n on any failure."""
    brief_block = f"\nCHANNEL STYLE BRIEF:\n{style_brief}\n" if style_brief else ""
    prompt = PLANNER_PROMPT.format(
        title=title.strip(), channel=channel, brief_block=brief_block, n=n,
    )
    try:
        raw = generate_text(prompt, temperature=0.85).strip()
        raw = _strip_fence(raw)
        items = json.loads(raw)
        out = [str(x).strip() for x in items if str(x).strip()]
        if not out:
            raise ValueError("empty")
        while len(out) < n:
            out.append(out[-1])
        return out[:n]
    except Exception:  # noqa: BLE001
        return [title] * n


def _strip_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    m = re.search(r"\[.*\]", text, re.DOTALL)
    return m.group(0) if m else text
