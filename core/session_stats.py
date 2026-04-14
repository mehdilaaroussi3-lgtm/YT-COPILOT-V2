"""Process-level counters surfaced as 'credits' in the sidebar.

Not persisted — resets each time YTcopilot studio restarts. Tracks calls so the
user can see what the tool has cost them this session.
"""
from __future__ import annotations

from threading import Lock

# Approximate per-call costs (USD) for surfacing only — not billing.
COST_PER_CALL = {
    "image": 0.134,    # gemini-3-pro-image-preview
    "vision": 0.005,   # gemini-2.5-pro vision describe
    "text": 0.003,     # gemini-2.5-pro text reasoning
}

_lock = Lock()
_counts: dict[str, int] = {"image": 0, "vision": 0, "text": 0}


def increment(kind: str) -> None:
    if kind not in _counts:
        return
    with _lock:
        _counts[kind] += 1


def snapshot() -> dict:
    with _lock:
        counts = dict(_counts)
    total_calls = sum(counts.values())
    cost = sum(counts[k] * COST_PER_CALL[k] for k in counts)
    return {
        "calls": counts,
        "total_calls": total_calls,
        "estimated_cost_usd": round(cost, 4),
    }


def reset() -> None:
    with _lock:
        for k in _counts:
            _counts[k] = 0
