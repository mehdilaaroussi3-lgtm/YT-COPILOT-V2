"""Path helpers for a single video dissection."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from cli import config as cfg

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def output_root() -> Path:
    p = Path(cfg.get("reverse.output_dir") or "data/reverse")
    if not p.is_absolute():
        p = REPO_ROOT / p
    p.mkdir(parents=True, exist_ok=True)
    return p


def tmp_root() -> Path:
    p = Path(cfg.get("reverse.tmp_dir") or "tmp_videos")
    if not p.is_absolute():
        p = REPO_ROOT / p
    p.mkdir(parents=True, exist_ok=True)
    return p


@dataclass
class Dirs:
    video_id: str
    root: Path
    frames: Path
    tmp: Path

    @property
    def metadata(self) -> Path: return self.root / "metadata.json"
    @property
    def scenes(self) -> Path: return self.root / "scenes.json"
    @property
    def transcript(self) -> Path: return self.root / "transcript.json"
    @property
    def audio(self) -> Path: return self.root / "audio_analysis.json"
    @property
    def blueprint(self) -> Path: return self.root / "blueprint.json"
    @property
    def mp4(self) -> Path: return self.tmp / f"{self.video_id}.mp4"
    @property
    def vtt(self) -> Path: return self.tmp / f"{self.video_id}.vtt"

    def scene_frame_a(self, idx: int) -> Path:
        return self.frames / f"scene_{idx:04d}.jpg"

    def scene_frame_b(self, idx: int) -> Path:
        return self.frames / f"scene_{idx:04d}_b.jpg"

    def scene_vision(self, idx: int) -> Path:
        return self.frames / f"scene_{idx:04d}.json"


def dirs_for(video_id: str) -> Dirs:
    root = output_root() / video_id
    frames = root / "frames"
    tmp = tmp_root()
    root.mkdir(parents=True, exist_ok=True)
    frames.mkdir(parents=True, exist_ok=True)
    return Dirs(video_id=video_id, root=root, frames=frames, tmp=tmp)
