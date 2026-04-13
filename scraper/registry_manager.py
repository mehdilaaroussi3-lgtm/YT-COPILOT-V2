"""Load and edit the channel registry YAML."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

REGISTRY_PATH = Path(__file__).resolve().parent / "channels_registry.yml"


def load_registry() -> dict[str, Any]:
    with REGISTRY_PATH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def save_registry(data: dict[str, Any]) -> None:
    with REGISTRY_PATH.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)


def list_niches() -> list[str]:
    return list(load_registry().keys())


def get_niche(niche: str) -> dict[str, Any]:
    reg = load_registry()
    if niche not in reg:
        raise KeyError(f"Niche '{niche}' not in registry. Available: {list(reg.keys())}")
    return reg[niche]


def add_channel(niche: str, name: str, channel_id: str,
                style_tags: list[str] | None = None, why: str = "") -> None:
    reg = load_registry()
    reg.setdefault(niche, {"channels": []})
    reg[niche]["channels"].append({
        "name": name,
        "channel_id": channel_id,
        "style_tags": style_tags or [],
        "why": why,
    })
    save_registry(reg)
