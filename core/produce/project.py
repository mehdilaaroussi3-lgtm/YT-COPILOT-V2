"""Project state management — project.json read/write."""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any

from cli import config as cfg

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RESOLUTIONS = {
    "4K": (3840, 2160),
    "2K": (2560, 1440),
    "1080p": (1920, 1080),
}


def productions_root() -> Path:
    p = REPO_ROOT / "data" / "productions"
    p.mkdir(parents=True, exist_ok=True)
    return p


class Project:
    def __init__(self, name: str):
        self.name = name
        self.root = productions_root() / name
        self.root.mkdir(parents=True, exist_ok=True)
        self._path = self.root / "project.json"
        self._data: dict[str, Any] = self._load()

    # ------------------------------------------------------------------ paths
    @property
    def script_path(self) -> Path: return self.root / "script.json"
    @property
    def audio_dir(self) -> Path:
        p = self.root / "audio"; p.mkdir(exist_ok=True); return p
    @property
    def output_dir(self) -> Path:
        p = self.root / "output"; p.mkdir(exist_ok=True); return p

    def section_dir(self, section_id: str) -> Path:
        p = self.root / "sections" / section_id
        p.mkdir(parents=True, exist_ok=True)
        return p

    # --------------------------------------------------------------- persistence
    def _load(self) -> dict:
        if self._path.exists():
            return json.loads(self._path.read_text(encoding="utf-8"))
        return {}

    def save(self) -> None:
        self._path.write_text(
            json.dumps(self._data, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    # ---------------------------------------------------------------- accessors
    def get(self, key: str, default=None):
        return self._data.get(key, default)

    def set(self, key: str, value) -> None:
        self._data[key] = value
        self.save()

    def init(self, *, blueprint_path: str, topic: str, resolution: str,
             voice_id: str, duration_hint: str) -> None:
        self._data.update({
            "name": self.name,
            "blueprint_path": blueprint_path,
            "topic": topic,
            "resolution": resolution,
            "voice_id": voice_id,
            "duration_hint": duration_hint,
            "section_statuses": {},
            "created_at": dt.datetime.now(dt.UTC).isoformat(),
        })
        self.save()

    # ----------------------------------------------------------- section status
    def section_status(self, section_id: str) -> str:
        return self._data.get("section_statuses", {}).get(section_id, "pending")

    def set_section_status(self, section_id: str, status: str) -> None:
        ss = self._data.setdefault("section_statuses", {})
        ss[section_id] = status
        self.save()

    # --------------------------------------------------------- resolution helpers
    @property
    def resolution(self) -> str:
        return self._data.get("resolution", "4K")

    @property
    def res_wh(self) -> tuple[int, int]:
        return RESOLUTIONS.get(self.resolution, RESOLUTIONS["2K"])

    @property
    def voice_id(self) -> str:
        return self._data.get("voice_id", "")

    @property
    def topic(self) -> str:
        return self._data.get("topic", "")

    @property
    def blueprint_path(self) -> Path:
        return Path(self._data.get("blueprint_path", ""))

    @property
    def music_path(self) -> Path | None:
        p = self.audio_dir / "music.mp3"
        return p if p.exists() else None

    def final_output(self) -> Path:
        return self.output_dir / f"final_{self.resolution}.mp4"
