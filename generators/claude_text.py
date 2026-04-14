"""Claude CLI text bridge.

Shells out to the local `claude` CLI (`claude -p <prompt> --output-format text`)
to run all text-reasoning tasks through Claude instead of Gemini. Image and
vision work stays on the Gemini API — see generators/gemini_client.py and
core/channel_text_dna.build_text_dna.

See CLAUDE.md at the repo root for the routing rule.
"""
from __future__ import annotations

import shutil
import subprocess
import time


class ClaudeTextError(RuntimeError):
    pass


_CLAUDE_BIN: str | None = None


def _resolve_bin() -> str:
    global _CLAUDE_BIN
    if _CLAUDE_BIN:
        return _CLAUDE_BIN
    for cand in ("claude", "claude.cmd"):
        found = shutil.which(cand)
        if found:
            _CLAUDE_BIN = found
            return found
    raise ClaudeTextError("`claude` CLI not found on PATH")


def generate_text(prompt: str, model: str | None = None,
                   temperature: float = 0.4) -> str:
    """One-shot text generation via the Claude CLI.

    `model` and `temperature` are accepted for signature compatibility with
    the old Gemini path but ignored — Claude CLI uses its configured model
    and sampling. Prompts already encode the determinism they need.
    """
    del model, temperature
    bin_path = _resolve_bin()

    last_err: str | None = None
    for attempt in range(2):
        try:
            proc = subprocess.run(
                [bin_path, "-p", prompt, "--output-format", "text"],
                capture_output=True, text=True, timeout=180,
                encoding="utf-8", errors="replace",
            )
            if proc.returncode != 0:
                last_err = f"exit {proc.returncode}: {(proc.stderr or '')[:400]}"
            else:
                out = (proc.stdout or "").strip()
                if out:
                    try:
                        from core.session_stats import increment
                        increment("text")
                    except Exception:  # noqa: BLE001
                        pass
                    return out
                last_err = "empty"
        except subprocess.TimeoutExpired:
            last_err = "timeout"
        except Exception as e:  # noqa: BLE001
            last_err = f"{type(e).__name__}: {e}"

        if attempt == 0:
            time.sleep(2.0)

    raise ClaudeTextError(f"Claude text generation failed: {last_err}")
