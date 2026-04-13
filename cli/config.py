"""Global config loader. Reads config.yml at repo root."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / "config.yml"
EXAMPLE_PATH = REPO_ROOT / "config.yml.example"


class ConfigError(Exception):
    pass


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        raise ConfigError(
            f"config.yml not found at {CONFIG_PATH}. "
            f"Copy {EXAMPLE_PATH.name} to config.yml and fill in your values."
        )
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def get(path: str, default: Any = None) -> Any:
    """Dot-path lookup, e.g. get('google_cloud.project_id')."""
    cfg = load_config()
    node: Any = cfg
    for part in path.split("."):
        if not isinstance(node, dict) or part not in node:
            return default
        node = node[part]
    return node
