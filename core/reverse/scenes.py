"""Stage 3: scene detection via PySceneDetect."""
from __future__ import annotations

from pathlib import Path

from cli import config as cfg


def detect_scenes(video: Path) -> list[dict]:
    """Return list of {idx, start, end, duration} for each detected scene."""
    from scenedetect import ContentDetector, SceneManager, open_video

    threshold = float(cfg.get("reverse.scene_threshold") or 27.0)
    vid = open_video(str(video))
    sm = SceneManager()
    sm.add_detector(ContentDetector(threshold=threshold))
    sm.detect_scenes(video=vid, show_progress=False)
    cuts = sm.get_scene_list()

    scenes: list[dict] = []
    if not cuts:
        # Single-scene fallback for videos without detectable cuts
        dur = float(vid.duration.get_seconds()) if hasattr(vid, "duration") else 0.0
        return [{"idx": 1, "start": 0.0, "end": dur, "duration": dur}]

    for i, (start, end) in enumerate(cuts, start=1):
        s = float(start.get_seconds())
        e = float(end.get_seconds())
        scenes.append({"idx": i, "start": s, "end": e, "duration": e - s})
    return scenes


def downsample(scenes: list[dict], max_scenes: int) -> list[dict]:
    """Structurally sample scenes down to max_scenes.

    Naive uniform sampling loses the hook and closer — the most formula-
    defining zones. Instead we allocate budget across three zones:

      Hook   (first 10% of duration) → 20% of budget  — captures opening style
      Body   (10% – 90%)             → 60% of budget  — representative formula
      Closer (last 10%)              → 20% of budget  — CTA + payoff style

    This gives the DNA synthesiser a statistically sound sample of the
    channel's formula with far fewer scenes.
    """
    if len(scenes) <= max_scenes:
        return scenes

    if not scenes:
        return scenes

    total_dur = scenes[-1]["end"] - scenes[0]["start"]
    hook_end   = scenes[0]["start"] + total_dur * 0.10
    closer_start = scenes[0]["start"] + total_dur * 0.90

    hook_scenes   = [s for s in scenes if s["start"] <  hook_end]
    body_scenes   = [s for s in scenes if hook_end <= s["start"] < closer_start]
    closer_scenes = [s for s in scenes if s["start"] >= closer_start]

    n_hook   = max(1, round(max_scenes * 0.20))
    n_closer = max(1, round(max_scenes * 0.20))
    n_body   = max(1, max_scenes - n_hook - n_closer)

    def _uniform(pool: list[dict], n: int) -> list[dict]:
        if not pool:
            return []
        if len(pool) <= n:
            return pool
        step = len(pool) / n
        return [pool[int(i * step)] for i in range(n)]

    kept = (
        _uniform(hook_scenes,   n_hook)
        + _uniform(body_scenes,   n_body)
        + _uniform(closer_scenes, n_closer)
    )

    # Deduplicate (zones can overlap on short videos) and re-index
    seen: set[int] = set()
    deduped: list[dict] = []
    for sc in kept:
        if sc["idx"] not in seen:
            seen.add(sc["idx"])
            deduped.append(sc)

    deduped.sort(key=lambda s: s["start"])
    for new_i, sc in enumerate(deduped, start=1):
        sc["idx"] = new_i
    return deduped
