"""Helpers for reading outlier thumbnails out of the SQLite DB for the UI.

Home page calls `random_outliers()`. Search hits `search_outliers()`.
Both union:
  (a) videos from curated channels_registry.yml that happened to be scanned
  (b) videos from user-added `tracked_channels`
— so the home feed reflects everything the user has in their local index.
"""
from __future__ import annotations

import random
from typing import Any

from data.db import db


def _hydrate(row: dict, d) -> dict:
    vid = row["video_id"]
    # .pks returns column *names*, not values — use get() with try/except
    try:
        thumb = d["thumbnails"].get(vid)
    except Exception:  # noqa: BLE001
        thumb = None
    channel = None
    cid = row.get("channel_id") or ""
    if cid:
        try:
            channel = d["channels"].get(cid)
        except Exception:  # noqa: BLE001
            pass
        if channel is None:
            try:
                channel = d["tracked_channels"].get(cid)
            except Exception:  # noqa: BLE001
                pass
    niche = (channel or {}).get("niche") or (channel or {}).get("niche_override") or ""
    return {
        "video_id": vid,
        "title": row.get("title", ""),
        "views": row.get("views", 0),
        "outlier_score": row.get("outlier_score", 0),
        "published_at": row.get("published_at", ""),
        "channel_id": row.get("channel_id", ""),
        "channel_name": (channel or {}).get("name", ""),
        "niche": niche,
        "thumbnail_path": (thumb or {}).get("file_path", ""),
        # hqdefault (480x360) is guaranteed to exist for EVERY YouTube video.
        # maxresdefault often 404s → browser shows broken image / alt text.
        "yt_thumb_url": f"https://img.youtube.com/vi/{vid}/hqdefault.jpg",
        "yt_url": f"https://www.youtube.com/watch?v={vid}",
        "style_tags": (thumb or {}).get("style_tags", ""),
    }


def _is_short_video(title: str) -> bool:
    """Filter out shorts by hashtag (belt-and-suspenders; shorts should be excluded during scraping)."""
    return "#shorts" in title.lower() or "#short" in title.lower()


def random_outliers(limit: int = 100, min_score: float = 2.0) -> list[dict[str, Any]]:
    """Return top-scoring outliers with channel diversity.

    First pass: best video per channel (sorted by score).
    Second pass: fill remaining slots with next-best videos across all channels.
    Result is sorted by outlier_score desc so the highest performers appear first.
    Shorts are excluded as a safety filter.
    """
    d = db()
    rows = list(d["videos"].rows_where(
        "outlier_score >= ?", [min_score],
        order_by="outlier_score desc",
    ))
    if not rows:
        return []

    # Filter out shorts (belt-and-suspenders; should already be filtered at scrape time)
    rows = [r for r in rows if not _is_short_video(r.get("title", ""))]

    # First pass — one top video per channel
    seen: set[str] = set()
    diverse: list[dict] = []
    for r in rows:
        cid = r.get("channel_id") or ""
        if cid in seen:
            continue
        seen.add(cid)
        diverse.append(r)
        if len(diverse) >= limit:
            break

    # Second pass — fill remaining slots with next-best videos (any channel)
    if len(diverse) < limit:
        taken = {r["video_id"] for r in diverse}
        for r in rows:
            if r["video_id"] in taken:
                continue
            diverse.append(r)
            if len(diverse) >= limit:
                break

    # Shuffle for fresh ordering every load (diversity selection already guarantees quality)
    random.shuffle(diverse)
    return [_hydrate(r, d) for r in diverse]


def search_outliers(query: str = "", niche: str | None = None,
                    channel_id: str | None = None,
                    limit: int = 100) -> list[dict[str, Any]]:
    d = db()
    clauses = ["outlier_score >= 1"]
    args: list = []
    if query:
        clauses.append("LOWER(title) LIKE ?")
        args.append(f"%{query.lower()}%")
    if channel_id:
        clauses.append("channel_id = ?")
        args.append(channel_id)

    where = " AND ".join(clauses)
    rows = list(d["videos"].rows_where(where, args,
                                        order_by="outlier_score desc",
                                        limit=limit))
    # Filter out shorts
    rows = [r for r in rows if not _is_short_video(r.get("title", ""))]
    hydrated = [_hydrate(r, d) for r in rows]
    if niche:
        # Soft filter: keep rows whose channel niche matches (if we have it)
        d2 = db()
        niched_ids = {r["channel_id"] for r in d2["channels"].rows_where(
            "niche = ?", [niche]
        )}
        hydrated = [h for h in hydrated if h["channel_id"] in niched_ids or not h["channel_id"]]
    return hydrated


def search_by_channels(channel_ids: list[str], limit: int = 200) -> list[dict[str, Any]]:
    """Return all outlier videos for a given list of channel IDs, sorted by score."""
    if not channel_ids:
        return []
    d = db()
    placeholders = ",".join("?" * len(channel_ids))
    rows = list(d["videos"].rows_where(
        f"channel_id IN ({placeholders})",
        channel_ids,
        order_by="outlier_score desc",
        limit=limit,
    ))
    return [_hydrate(r, d) for r in rows]


def get_outlier(video_id: str) -> dict | None:
    d = db()
    try:
        return _hydrate(d["videos"].get(video_id), d)
    except Exception:  # noqa: BLE001
        return None


# Niches whose thumbnails are overwhelmingly faceless / illustrated / text-heavy.
# Matches the user's example set: history explainers, finance/money, ai/hacker,
# true crime, documentary, geopolitics — all long-form faceless-channel niches.
FACELESS_NICHES = {
    "history_education", "finance_money", "science_education",
    "ai_tech", "documentary_essay", "true_crime", "space_astronomy",
    "psychology_self_help", "geopolitics_news", "business_entrepreneur",
    "productivity_dev", "film_media_essay", "animation",
}


def premium_outliers(limit: int = 10, min_subs: int = 100_000,
                      min_score: float = 3.0, max_score: float = 25.0,
                      faceless_bias: bool = True) -> list[dict[str, Any]]:
    """Return outliers ONLY from premium channels (100k+ subs) with sane score range.

    Why: tiny channels with 1 viral video produce absurd outlier scores (6000x+)
    that are statistical junk, not signals. Premium channels with 3x–25x scores
    are where real packaging lessons live.

    When faceless_bias=True, prioritises faceless/illustrated niches (the visual
    style the user's channel is built around).
    """
    d = db()
    # Collect premium channel IDs split by niche bucket (faceless vs other)
    faceless_ids: set[str] = set()
    other_ids: set[str] = set()

    def _bucket(cid: str, niche: str) -> None:
        if faceless_bias and niche in FACELESS_NICHES:
            faceless_ids.add(cid)
        else:
            other_ids.add(cid)

    try:
        for r in d["channels"].rows_where(
            "subs >= ? OR median_views >= ?", [min_subs, 50_000]
        ):
            _bucket(r["channel_id"], r.get("niche") or "")
    except Exception:  # noqa: BLE001
        pass
    try:
        for r in d["tracked_channels"].rows_where("subs >= ?", [min_subs]):
            _bucket(r["channel_id"], r.get("niche_override") or r.get("niche") or "")
    except Exception:  # noqa: BLE001
        pass

    premium_ids = faceless_ids | other_ids
    if not premium_ids:
        rows = list(d["videos"].rows_where(
            "outlier_score >= ? AND outlier_score <= ?",
            [min_score, max_score], order_by="outlier_score desc", limit=limit * 8,
        ))
    else:
        placeholders = ",".join("?" * len(premium_ids))
        rows = list(d["videos"].rows_where(
            f"outlier_score >= ? AND outlier_score <= ? AND channel_id IN ({placeholders})",
            [min_score, max_score, *premium_ids],
            order_by="outlier_score desc", limit=limit * 8,
        ))

    rows = [r for r in rows if not _is_short_video(r.get("title", ""))]

    # Split by faceless / other for weighted mix
    fl_rows = [r for r in rows if r.get("channel_id") in faceless_ids]
    ot_rows = [r for r in rows if r.get("channel_id") in other_ids]

    # Channel diversity — one top video per channel per bucket
    def _diversify(rs: list[dict]) -> list[dict]:
        seen: set[str] = set()
        out: list[dict] = []
        for r in rs:
            cid = r.get("channel_id") or ""
            if cid in seen:
                continue
            seen.add(cid)
            out.append(r)
        return out

    fl_rows = _diversify(fl_rows)
    ot_rows = _diversify(ot_rows)

    # Target 90% faceless, 10% other (as the user explicitly asked for)
    fl_quota = max(1, int(round(limit * 0.9))) if faceless_bias else limit // 2
    ot_quota = limit - fl_quota

    picked = fl_rows[:fl_quota] + ot_rows[:ot_quota]
    # Top up from whichever bucket has more if we under-filled
    if len(picked) < limit:
        leftovers = [r for r in (fl_rows[fl_quota:] + ot_rows[ot_quota:]) if r not in picked]
        picked.extend(leftovers[: (limit - len(picked))])

    random.shuffle(picked)
    return [_hydrate(r, d) for r in picked[:limit]]


def recent_outliers(limit: int = 6, min_score: float = 2.0) -> list[dict[str, Any]]:
    """Return most-recently-indexed outliers (by fetched_at DESC). Used by the Home page.

    Shorts are filtered out as they are long-format-only app.
    """
    d = db()
    rows = list(d["videos"].rows_where(
        "outlier_score >= ?", [min_score],
        order_by="fetched_at desc",
        limit=limit,
    ))
    # Filter out shorts
    rows = [r for r in rows if not _is_short_video(r.get("title", ""))]
    return [_hydrate(r, d) for r in rows]


def random_channels(limit: int = 30, niche: str | None = None) -> list[dict]:
    """Return a shuffled mix of curated + tracked channels with per-channel outlier stats."""
    d = db()

    # Pull curated channels
    curated_where = "niche = ?" if niche else "1=1"
    curated_args: list = [niche] if niche else []
    curated = list(d["channels"].rows_where(curated_where, curated_args))

    # Pull tracked channels (may have richer data: avatar, description, ai_summary)
    tracked_where = "niche_override = ?" if niche else "1=1"
    tracked_args: list = [niche] if niche else []
    tracked = list(d["tracked_channels"].rows_where(tracked_where, tracked_args))

    tracked_ids: set[str] = {r["channel_id"] for r in tracked}
    curated_deduped = [r for r in curated if r["channel_id"] not in tracked_ids]

    # Build per-channel video stats in Python (avoids SQLite version concerns)
    try:
        all_vids = list(d["videos"].rows_where(
            "outlier_score >= 2.0", [], order_by="outlier_score desc"
        ))
    except Exception:  # noqa: BLE001
        all_vids = []

    from collections import defaultdict
    ch_videos: dict[str, list] = defaultdict(list)
    for v in all_vids:
        cid = v.get("channel_id") or ""
        if cid:
            ch_videos[cid].append(v)

    def _ch_stats(cid: str) -> dict:
        vids = ch_videos.get(cid, [])
        if not vids:
            return {"outlier_count": 0, "top_score": 0.0, "top_video_ids": []}
        return {
            "outlier_count": len(vids),
            "top_score": round(vids[0]["outlier_score"], 2),
            "top_video_ids": [v["video_id"] for v in vids[:3]],
        }

    def _build(r: dict, source: str) -> dict:
        cid = r["channel_id"]
        vs = _ch_stats(cid)
        subs = r.get("subs") or 0
        return {
            "channel_id": cid,
            "name": r.get("name") or "",
            "handle": r.get("handle"),
            "subs": subs,
            "niche": r.get("niche_override") or r.get("niche") or "",
            "description": r.get("description"),
            "ai_summary": r.get("ai_summary"),
            "avatar_url": r.get("avatar_url"),
            "median_views": r.get("median_views") or 0.0,
            "outlier_count": vs["outlier_count"],
            "top_score": vs["top_score"],
            "top_video_ids": vs["top_video_ids"],
            "is_tracked": cid in tracked_ids,
            "source": source,
            # YPP eligibility threshold (1K subs is YouTube's minimum)
            "is_monetized_likely": subs >= 1_000,
        }

    all_ch = [_build(r, "tracked") for r in tracked] + [_build(r, "curated") for r in curated_deduped]

    # Quality gate: must have at least a name and some real data
    # Avatar is optional — letter fallback looks good; don't filter on it
    quality = [
        ch for ch in all_ch
        if ch.get("name")                                # must have a name
        and (
            ch["outlier_count"] >= 1                     # has scanned outlier videos
            or ch["subs"] >= 10_000                      # or has meaningful audience
            or ch.get("avatar_url")                      # or avatar already resolved
        )
    ]

    # Tier A: has outliers + meaningful subs → best signal
    # Tier B: has outliers, smaller channel → hidden gems
    # Tier C: big premium channel, not yet scanned
    tier_a = [ch for ch in quality if ch["outlier_count"] >= 1 and ch["subs"] >= 50_000]
    tier_b = [ch for ch in quality if ch["outlier_count"] >= 1 and ch["subs"] < 50_000]
    tier_c = [ch for ch in quality if ch["outlier_count"] == 0]

    for tier in (tier_a, tier_b, tier_c):
        random.shuffle(tier)

    return (tier_a + tier_b + tier_c)[:limit]


def outlier_stats() -> dict:
    """Count of outlier videos at each score tier (for Dashboard)."""
    d = db()
    try:
        tier_2x = d["videos"].count_where("outlier_score >= 2.0")
        tier_3x = d["videos"].count_where("outlier_score >= 3.0")
        tier_5x = d["videos"].count_where("outlier_score >= 5.0")
        tier_10x = d["videos"].count_where("outlier_score >= 10.0")
    except Exception:  # noqa: BLE001
        tier_2x = tier_3x = tier_5x = tier_10x = 0
    return {"tier_2x": tier_2x, "tier_3x": tier_3x, "tier_5x": tier_5x, "tier_10x": tier_10x}


def niche_stats() -> list[dict]:
    """Per-niche breakdown: channel count, video count, avg score, last scanned."""
    d = db()
    try:
        rows = d.execute(
            "SELECT c.niche, COUNT(DISTINCT c.channel_id) as ch_cnt, "
            "COUNT(v.video_id) as vid_cnt, AVG(v.outlier_score) as avg_sc, "
            "MAX(c.last_scanned) as last_sc "
            "FROM channels c LEFT JOIN videos v ON c.channel_id = v.channel_id "
            "AND v.outlier_score >= 2.0 "
            "GROUP BY c.niche ORDER BY vid_cnt DESC"
        ).fetchall()
        return [
            {
                "niche": r[0] or "unknown",
                "channel_count": r[1],
                "video_count": r[2],
                "avg_score": round(r[3], 2) if r[3] else 0.0,
                "last_scanned": r[4],
            }
            for r in rows if r[0]
        ]
    except Exception:  # noqa: BLE001
        return []


def style_tags_summary(top_n: int = 15) -> list[dict]:
    """Most frequent style tags across all indexed thumbnails (for Dashboard tag cloud)."""
    from collections import Counter
    d = db()
    try:
        rows = d.execute(
            "SELECT style_tags FROM thumbnails WHERE style_tags IS NOT NULL AND style_tags != ''"
        ).fetchall()
    except Exception:  # noqa: BLE001
        return []
    counter: Counter = Counter()
    for (tags,) in rows:
        for tag in tags.split(","):
            tag = tag.strip()
            if tag:
                counter[tag] += 1
    return [{"tag": tag, "count": cnt} for tag, cnt in counter.most_common(top_n)]


def available_niches() -> list[str]:
    """Distinct niche values across all channel sources (for filter dropdowns)."""
    d = db()
    niches: set[str] = set()
    try:
        for (n,) in d.execute(
            "SELECT DISTINCT niche FROM channels WHERE niche IS NOT NULL AND niche != ''"
        ).fetchall():
            niches.add(n)
    except Exception:  # noqa: BLE001
        pass
    try:
        for (n,) in d.execute(
            "SELECT DISTINCT niche_override FROM tracked_channels "
            "WHERE niche_override IS NOT NULL AND niche_override != ''"
        ).fetchall():
            niches.add(n)
    except Exception:  # noqa: BLE001
        pass
    return sorted(niches)
