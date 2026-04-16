"""Weekly background scan — populates outlier DB from seed registry + tracked channels.

Called automatically on server startup when any channel is stale (>7 days since
last scan, or never scanned). Also callable via POST /api/outliers/scan.

Quota impact: ~3 units per channel (1 for uploads playlist + 2 for video stats).
20 seed channels × 3 = ~60 units per weekly run — well within the free 10k/day quota.
"""
from __future__ import annotations

import datetime as dt
import threading
from typing import Any, Callable

from cli import config as cfg

SCAN_INTERVAL_DAYS = 7


def _channel_stale(channel_id: str, d) -> bool:
    """Return True if this channel has never been scanned or the scan is >7 days old."""
    for table in ("channels", "tracked_channels"):
        if table not in d.table_names():
            continue
        if channel_id not in d[table].pks:
            continue
        row = d[table].get(channel_id)
        last = (row or {}).get("last_scanned") or ""
        if not last:
            return True
        try:
            ts = dt.datetime.fromisoformat(last.replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=dt.timezone.utc)
            age = (dt.datetime.now(dt.timezone.utc) - ts).days
            return age >= SCAN_INTERVAL_DAYS
        except Exception:  # noqa: BLE001
            return True
    return True  # not in DB at all → must scan


def needs_scan() -> bool:
    """True if any seed channel is stale OR the videos table is empty."""
    from data.db import db
    from scraper.registry_manager import get_niche, list_niches
    d = db()
    # If videos table is completely empty, always scan
    if "videos" not in d.table_names() or d["videos"].count == 0:
        return True
    for niche in list_niches():
        cfg = get_niche(niche)
        for ch in cfg.get("channels", []):
            if _channel_stale(ch["channel_id"], d):
                return True
    return False


def scan_all_channels(
    force: bool = False,
    on_progress: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Scan all seed registry channels + user-tracked channels.

    Skips channels scanned within the last SCAN_INTERVAL_DAYS unless force=True.
    Returns summary dict: {"channels_scanned": N, "total_outliers": N}.
    """
    from agents.outlier_discovery import OutlierDiscoveryAgent
    from data.db import db
    from scraper.registry_manager import get_niche, list_niches

    def log(msg: str) -> None:
        print(f"[weekly-scan] {msg}")
        if on_progress:
            on_progress(msg)

    d = db()
    agent = OutlierDiscoveryAgent()

    scanned = 0
    total_outliers = 0

    # ── 1. Seed registry channels ────────────────────────────────────────────
    for niche in list_niches():
        cfg = get_niche(niche)
        for ch in cfg.get("channels", []):
            cid = ch["channel_id"]
            name = ch["name"]

            if not force and not _channel_stale(cid, d):
                log(f"  skip {name} (recently scanned)")
                continue

            log(f"  scanning {name} [{niche}]…")
            try:
                outliers = agent.scan_channel(
                    cid, name,
                    min_score=cfg.get("outlier.min_score", 3.0),
                    download=True,
                )
                # Tag channel with niche so _hydrate() can read it
                d["channels"].upsert(
                    {"channel_id": cid, "niche": niche},
                    pk="channel_id",
                    alter=True,
                )
                total_outliers += len(outliers)
                scanned += 1
                log(f"    → {len(outliers)} outliers")
            except Exception as e:  # noqa: BLE001
                log(f"    [error] {e}")

    # ── 2. User-tracked channels ─────────────────────────────────────────────
    if "tracked_channels" in d.table_names():
        for tc in list(d["tracked_channels"].rows):
            cid = tc["channel_id"]
            name = tc.get("name") or cid

            if not force and not _channel_stale(cid, d):
                continue

            log(f"  scanning tracked: {name}…")
            try:
                outliers = agent.scan_channel(
                    cid, name,
                    min_score=cfg.get("outlier.tracked_min_score", 3.0),
                    download=True,
                )
                total_outliers += len(outliers)
                scanned += 1
                log(f"    → {len(outliers)} outliers")
            except Exception as e:  # noqa: BLE001
                log(f"    [error] {e}")

    log(f"Done. {scanned} channels scanned, {total_outliers} outliers indexed.")
    return {"channels_scanned": scanned, "total_outliers": total_outliers}


def start_background_scan(force: bool = False) -> threading.Thread:
    """Launch scan_all_channels in a daemon background thread."""
    t = threading.Thread(
        target=scan_all_channels,
        kwargs={"force": force},
        daemon=True,
        name="weekly-scan",
    )
    t.start()
    return t
