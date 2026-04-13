"""Channel profile loader."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

PROFILES_DIR = Path(__file__).resolve().parent.parent / "channels" / "profiles"


class ProfileError(Exception):
    pass


def load_profile(name: str) -> dict[str, Any]:
    """Load a channel profile.

    Accepts a profile filename stem OR a tracked YouTube channel_id ('UC...').
    For a tracked channel, the default profile is used as a base and the
    tracked row's name/handle/id are overlaid — one channel identity, no
    separate 'brand profile' layer.
    """
    raw = (name or "default").strip()
    if raw.startswith("UC") and len(raw) >= 20:
        return _profile_for_tracked(raw)

    key = raw.lower()
    candidate = PROFILES_DIR / f"{key}.yml"
    if not candidate.exists():
        if key == "default":
            raise ProfileError(f"default.yml missing at {PROFILES_DIR}")
        candidate = PROFILES_DIR / "default.yml"
    with candidate.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    data["_name"] = key
    return data


def _profile_for_tracked(channel_id: str) -> dict[str, Any]:
    from data.db import db
    d = db()
    row = d["tracked_channels"].get(channel_id) if channel_id in d["tracked_channels"].pks else None
    if row is None and channel_id in d["channels"].pks:
        row = d["channels"].get(channel_id)

    base_path = PROFILES_DIR / "default.yml"
    with base_path.open("r", encoding="utf-8") as f:
        base = yaml.safe_load(f) or {}

    if row:
        base["name"] = row.get("name") or row.get("handle") or channel_id
        base["handle"] = row.get("handle") or ""
        base["channel_id"] = channel_id
    base["_name"] = channel_id
    return base


def list_profiles() -> list[dict[str, Any]]:
    out = []
    for p in sorted(PROFILES_DIR.glob("*.yml")):
        try:
            data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
            out.append({
                "key": p.stem,
                "name": data.get("name", p.stem),
                "niche": data.get("niche", ""),
            })
        except Exception:  # noqa: BLE001
            continue
    return out


def save_profile(name: str, data: dict[str, Any]) -> Path:
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    path = PROFILES_DIR / f"{name}.yml"
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)
    return path
