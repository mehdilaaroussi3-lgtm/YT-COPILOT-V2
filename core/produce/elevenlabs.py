"""ElevenLabs integration: voice listing, interactive pick, TTS generation."""
from __future__ import annotations

import random
import time
import webbrowser

import httpx

from cli import config as cfg

BASE = "https://api.elevenlabs.io/v1"


class ElevenLabsError(RuntimeError):
    pass


def _key() -> str:
    k = cfg.get("elevenlabs.api_key") or ""
    if not k or k.startswith("your-"):
        raise ElevenLabsError(
            "elevenlabs.api_key not set in config.yml — add it and retry."
        )
    return k


def list_voices() -> list[dict]:
    """Return [{id, name, labels, preview_url}] sorted by name."""
    with httpx.Client(timeout=30.0) as c:
        r = c.get(f"{BASE}/voices", headers={"xi-api-key": _key()})
    if r.status_code != 200:
        raise ElevenLabsError(f"ElevenLabs voices fetch failed: {r.status_code}")
    voices = r.json().get("voices", [])
    return sorted(
        [
            {
                "id": v["voice_id"],
                "name": v.get("name", ""),
                "labels": v.get("labels") or {},
                "preview_url": v.get("preview_url") or "",
            }
            for v in voices
        ],
        key=lambda x: x["name"].lower(),
    )


def pick_voice_interactive() -> str:
    """Print voice table, open previews on request, return chosen voice_id."""
    from rich.console import Console
    from rich.table import Table

    console = Console()
    voices = list_voices()

    table = Table(title="ElevenLabs Voices", show_lines=False)
    table.add_column("#", style="dim", width=4)
    table.add_column("Name", style="bold cyan")
    table.add_column("Accent / Style")
    table.add_column("ID", style="dim")

    for i, v in enumerate(voices, start=1):
        labels = v["labels"]
        accent = labels.get("accent") or labels.get("language") or ""
        style = labels.get("use case") or labels.get("description") or ""
        tag = f"{accent} / {style}".strip(" /")
        table.add_row(str(i), v["name"], tag, v["id"])

    console.print(table)
    console.print("\n[dim]Type a number to preview/select, or type a voice ID directly.[/]")

    while True:
        raw = input("Voice (number or ID): ").strip()
        if not raw:
            continue
        # Direct ID
        if len(raw) > 6 and not raw.isdigit():
            match = next((v for v in voices if v["id"] == raw), None)
            if match:
                return _confirm_and_save(match, console)
            console.print(f"[red]ID not found: {raw}[/]")
            continue
        # Number
        try:
            idx = int(raw) - 1
            if 0 <= idx < len(voices):
                v = voices[idx]
                if v["preview_url"]:
                    console.print(f"[dim]Opening preview for {v['name']}…[/]")
                    webbrowser.open(v["preview_url"])
                return _confirm_and_save(v, console)
        except ValueError:
            pass
        console.print("[red]Invalid input.[/]")


def _confirm_and_save(voice: dict, console) -> str:
    console.print(f"\nSelected: [bold cyan]{voice['name']}[/] ({voice['id']})")
    confirm = input("Use this voice? [Y/n]: ").strip().lower()
    if confirm in ("", "y", "yes"):
        _save_default(voice["id"])
        return voice["id"]
    return pick_voice_interactive()


def _save_default(voice_id: str) -> None:
    """Write default_voice_id back to config.yml."""
    from cli.config import CONFIG_PATH
    try:
        text = CONFIG_PATH.read_text(encoding="utf-8")
        if "default_voice_id:" in text:
            import re
            text = re.sub(
                r'(default_voice_id:\s*)["\']?[^"\'\n]*["\']?',
                f'\\g<1>"{voice_id}"',
                text,
            )
        else:
            text = text.rstrip() + f'\n  default_voice_id: "{voice_id}"\n'
        CONFIG_PATH.write_text(text, encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass  # non-critical


def generate_vo(text: str, voice_id: str) -> bytes:
    """Generate TTS audio for text. Returns raw MP3 bytes."""
    api_key = _key()
    model = cfg.get("elevenlabs.model") or "eleven_multilingual_v2"
    url = f"{BASE}/text-to-speech/{voice_id}"
    body = {
        "text": text,
        "model_id": model,
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
    }

    last_err: str = ""
    for attempt in range(5):
        try:
            with httpx.Client(timeout=60.0) as c:
                r = c.post(url, json=body,
                           headers={"xi-api-key": api_key,
                                    "Content-Type": "application/json",
                                    "Accept": "audio/mpeg"})
            if r.status_code == 429:
                last_err = "429"
            elif r.status_code != 200:
                raise ElevenLabsError(f"ElevenLabs TTS error {r.status_code}: {r.text[:200]}")
            else:
                return r.content
        except (httpx.TimeoutException, httpx.NetworkError) as e:
            last_err = type(e).__name__
        delay = min(10.0 * (2 ** attempt), 60.0) * (0.5 + random.random() * 0.5)
        time.sleep(delay)
    raise ElevenLabsError(f"TTS failed after 5 attempts: {last_err}")
