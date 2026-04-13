"""Natural language thumbnail refinement via Gemini multi-turn editing."""
from __future__ import annotations

import datetime as dt
from pathlib import Path

from core.data_rules import ANTI_AI_DIRECTIVES
from generators.gemini_client import GeminiImageClient


REFINE_TEMPLATE = """\
This is an existing YouTube thumbnail. Apply this edit:

{instruction}

Keep the same composition and subject identity unless the edit explicitly
asks otherwise. Output the edited image at 16:9 widescreen.

{anti_ai}
"""


def refine_thumbnail(image_path: Path, instruction: str,
                      output_dir: Path | None = None,
                      extra_reference: Path | None = None) -> Path:
    """Send existing thumbnail + NL edit to Gemini, save result alongside source."""
    client = GeminiImageClient.from_config()
    prompt = REFINE_TEMPLATE.format(instruction=instruction, anti_ai=ANTI_AI_DIRECTIVES)
    refs = [image_path]
    if extra_reference is not None:
        refs.append(extra_reference)
    result = client.generate(prompt, reference_images=refs)

    out_dir = output_dir or image_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = dt.datetime.now().strftime("%H%M%S")
    out_path = out_dir / f"{image_path.stem}_refined_{ts}{result.extension}"
    out_path.write_bytes(result.data)
    return out_path
