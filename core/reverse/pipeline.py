"""URE orchestrator — runs the 11-stage pipeline, each stage idempotent."""
from __future__ import annotations

import datetime as dt
import json
import re
import shutil
from pathlib import Path
from typing import Callable

from cli import config as cfg
from core.reverse import (
    audio as audio_stage,
    blueprint as blueprint_stage,
    classify,
    download as download_stage,
    keyframes,
    motion,
    probe as probe_stage,
    scenes as scenes_stage,
    script_formula,
    transcript as transcript_stage,
    vision,
)
from core.reverse.paths import Dirs, dirs_for, output_root


def _slugify(text: str, max_len: int = 80) -> str:
    """Convert a video title to a safe filesystem folder name."""
    slug = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', text)
    slug = re.sub(r'_+', '_', slug).strip('_ ')
    return slug[:max_len].rstrip('. ') or "untitled"

Progress = Callable[[str], None]

STAGES = ("download", "probe", "scenes", "keyframes", "motion", "vision",
          "classify", "transcript", "audio", "script_formula", "blueprint")


def _write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _should_skip(force: bool, force_stage: str | None, stage: str, artifact: Path) -> bool:
    if force:
        return False
    if force_stage == stage:
        return False
    return artifact.exists()


def reverse(url: str, *, force: bool = False, force_stage: str | None = None,
            max_scenes: int | None = None, whisper_enabled: bool | None = None,
            first_seconds: int | None = None,
            progress: Progress = print) -> Path:
    """Dissect a YouTube video. Returns the per-video output directory."""
    video_id = download_stage.extract_video_id(url)
    dirs: Dirs = dirs_for(video_id)
    progress(f"[URE] {video_id} → {dirs.root}")

    # --- Stage 1: download ----------------------------------------------
    info: dict
    if _should_skip(force, force_stage, "download", dirs.metadata):
        info = _read_json(dirs.metadata)
    else:
        info = download_stage.download(url, dirs, progress=progress,
                                       first_seconds=first_seconds)
        info["url"] = url
        info["video_id"] = video_id
        info["processed_at"] = dt.datetime.now(dt.UTC).isoformat()
        _write_json(dirs.metadata, info)

    # --- Rename output folder to video title ----------------------------
    title = (info.get("title") or "").strip()
    if title:
        slug = _slugify(title)
        new_root = output_root() / slug
        if dirs.root.resolve() != new_root.resolve():
            if not new_root.exists():
                dirs.root.rename(new_root)
            else:
                # title folder already exists (resume run) — drop the
                # freshly-created video_id stub and switch to it
                shutil.rmtree(dirs.root, ignore_errors=True)
            new_root.mkdir(parents=True, exist_ok=True)
            new_frames = new_root / "frames"
            new_frames.mkdir(parents=True, exist_ok=True)
            dirs = Dirs(video_id=video_id, root=new_root,
                        frames=new_frames, tmp=dirs.tmp)
            progress(f"[URE] folder → {dirs.root.name}")

    # --- Stage 2: probe -------------------------------------------------
    if "fps" not in info or force or force_stage == "probe":
        progress("probing video")
        info.update(probe_stage.probe(dirs.mp4))
        _write_json(dirs.metadata, info)
    duration_s = float(info.get("duration_s") or 0.0)

    # --- Stage 3: scenes -----------------------------------------------
    scenes: list[dict]
    if _should_skip(force, force_stage, "scenes", dirs.scenes):
        scenes = _read_json(dirs.scenes)
    else:
        progress("detecting scenes")
        scenes = scenes_stage.detect_scenes(dirs.mp4)
        cap = max_scenes or int(cfg.get("reverse.max_scenes_default") or 25)
        if len(scenes) > cap:
            progress(f"structural-sampling {cap} of {len(scenes)} scenes (hook/body/closer)")
            scenes = scenes_stage.downsample(scenes, cap)
        _write_json(dirs.scenes, scenes)
    progress(f"scenes: {len(scenes)}")

    # --- Stage 4: keyframes --------------------------------------------
    progress("extracting keyframe pairs")
    keyframes.extract_pairs(dirs.mp4, scenes, dirs)

    # --- Stage 5: motion analysis --------------------------------------
    motion_enabled = cfg.get("reverse.motion_analysis_enabled")
    motion_enabled = True if motion_enabled is None else bool(motion_enabled)
    motion_results: list[dict] = []
    if motion_enabled:
        progress("analyzing motion signatures")
        for sc in scenes:
            sig = motion.signature(dirs.scene_frame_a(sc["idx"]),
                                    dirs.scene_frame_b(sc["idx"]))
            motion_results.append(sig)
    else:
        motion_results = [{"label": "unknown"} for _ in scenes]

    # --- Stage 6: vision -----------------------------------------------
    # Use batched calls: 8 scenes per Gemini call instead of 1 per scene.
    # Only frame_a (midpoint keyframe) is sent — frame_b was only useful for
    # motion comparison, which the motion module already handles via optical flow.
    progress(f"gemini vision on {len(scenes)} scenes (batched)")
    cached_indices: set[int] = set()
    vision_results: list[dict] = [{}] * len(scenes)

    # Load already-cached results, collect indices that need processing
    needs_vision: list[tuple[int, dict]] = []   # (list_index, scene)
    for i, sc in enumerate(scenes):
        vpath = dirs.scene_vision(sc["idx"])
        if vpath.exists() and not (force or force_stage == "vision"):
            vision_results[i] = _read_json(vpath)
            cached_indices.add(i)
        else:
            needs_vision.append((i, sc))

    if needs_vision:
        frames = [dirs.scene_frame_a(sc["idx"]) for _, sc in needs_vision]
        batch_out = vision.label_scenes_batch(frames)
        for (i, sc), result in zip(needs_vision, batch_out):
            vision_results[i] = result
            _write_json(dirs.scene_vision(sc["idx"]), result)

    # --- Stage 7: classification fusion --------------------------------
    progress("classifying production types")
    scenes_full: list[dict] = []
    scenes_fused: list[dict] = []
    for sc, m, v in zip(scenes, motion_results, vision_results):
        fused = classify.fuse_scene(m, v)
        merged = {
            **sc,
            "motion_signature": m.get("label"),
            "motion_stats": {k: m.get(k) for k in ("flow_mean", "residual_ratio", "localized") if k in m},
            "production_type": fused["production_type"],
            "production_confidence": fused["confidence"],
            "production_evidence": fused["evidence"],
            "shot_type": v.get("shot_type"),
            "motion_type": v.get("motion_type"),
            "description": v.get("description", ""),
            "on_screen_text": v.get("on_screen_text", ""),
            "dominant_colors": v.get("dominant_colors", []),
            "has_face": v.get("has_face", False),
            "style_tags": v.get("style_tags", []),
            "keyframe_path": str(dirs.scene_frame_a(sc["idx"]).relative_to(dirs.root)),
        }
        scenes_full.append(merged)
        scenes_fused.append({
            "production_type": fused["production_type"],
            "confidence": fused["confidence"],
            "duration": sc["duration"],
            "evidence": fused["evidence"],
        })
    _write_json(dirs.scenes, scenes_full)
    formula = classify.video_formula(scenes_fused)

    # --- Stage 8: transcript -------------------------------------------
    if _should_skip(force, force_stage, "transcript", dirs.transcript):
        transcript_aligned = _read_json(dirs.transcript)
    else:
        progress("transcribing")
        w_enabled = whisper_enabled
        if w_enabled is None:
            w_enabled = bool(cfg.get("reverse.whisper_enabled", True))
        raw_segs = transcript_stage.transcribe(dirs.mp4, dirs.vtt, whisper_enabled=w_enabled)
        transcript_aligned = transcript_stage.align_to_scenes(raw_segs, scenes)
        _write_json(dirs.transcript, transcript_aligned)

    # --- Stage 9: audio ------------------------------------------------
    if _should_skip(force, force_stage, "audio", dirs.audio):
        audio_data = _read_json(dirs.audio)
    else:
        progress("analyzing audio")
        try:
            audio_data = audio_stage.analyze(dirs.mp4, scenes)
        except Exception as e:  # noqa: BLE001
            progress(f"(audio analysis failed: {e} — continuing without)")
            audio_data = {"available": False}
        _write_json(dirs.audio, audio_data)

    # --- Stage 10: script formula --------------------------------------
    progress("extracting script formula (claude)")
    script_f = script_formula.extract(transcript_aligned)

    # --- Stage 11: blueprint -------------------------------------------
    progress("assembling blueprint (claude)")
    bp = blueprint_stage.build(
        video_id=video_id,
        metadata=info,
        formula=formula,
        scenes_full=scenes_full,
        duration_s=duration_s,
        transcript_aligned=transcript_aligned,
        script_formula=script_f,
        audio=audio_data,
    )
    _write_json(dirs.blueprint, bp)

    # --- DB indexing ----------------------------------------------------
    try:
        from data.db import db
        d = db()
        if "reverse_videos" in d.table_names():
            d["reverse_videos"].upsert({
                "video_id": video_id,
                "url": url,
                "title": info.get("title") or "",
                "channel": info.get("channel") or "",
                "duration_s": duration_s,
                "production_formula": formula.get("primary"),
                "scenes_count": len(scenes_full),
                "processed_at": info.get("processed_at"),
            }, pk="video_id", alter=True)
        if "reverse_scenes" in d.table_names():
            # purge prior rows for idempotence
            d["reverse_scenes"].delete_where("video_id = ?", [video_id])
            for sc in scenes_full:
                d["reverse_scenes"].insert({
                    "video_id": video_id,
                    "idx": sc["idx"],
                    "start_s": sc["start"],
                    "end_s": sc["end"],
                    "production_type": sc.get("production_type"),
                    "shot_type": sc.get("shot_type"),
                    "keyframe_path": sc.get("keyframe_path"),
                }, alter=True)
    except Exception as e:  # noqa: BLE001
        progress(f"(db indexing skipped: {e})")

    progress(f"[URE] done → {dirs.blueprint}")
    return dirs.root
