"""Production pipeline orchestrator.

Stages:
  1. Script generation (Claude)
  2. Section boundary confirmation (CLI gate)
  3. Per-section loop:
     a. Image generation (Gemini)
     b. VO generation (ElevenLabs) → duration measured → this IS frame duration
     c. Ken Burns clip render (FFmpeg zoompan)
     d. Review gate (open images + play VO, Enter/R/Q)
     e. Section assembly
  4. Final assembly (FFmpeg concat + optional music mix)
  5. Thumbnail generation (channel-style copycat, saved to project output dir)
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from rich.console import Console

from core.produce import assembler, gate, image_gen, kenburns, script_gen, vo_gen
from core.produce.project import Project

Progress = Callable[[str], None]
console = Console()


def _print_section_preview(sections: list[dict]) -> None:
    console.print("\n[bold]Proposed sections:[/]")
    for sec in sections:
        label = sec.get("label") or sec.get("id")
        scenes = sec.get("scenes", [])
        console.print(f"  [cyan]{label}[/] — {len(scenes)} scene(s)")
        for sc in scenes[:2]:
            vo = (sc.get("vo") or "")[:80]
            console.print(f"    [dim]#{sc['idx']}:[/] {vo}…")
        if len(scenes) > 2:
            console.print(f"    [dim]… +{len(scenes) - 2} more[/]")
    console.print()


def _confirm_sections(script: dict) -> bool:
    _print_section_preview(script.get("sections", []))
    console.print("[dim]Edit script.json to adjust, then re-run.[/]")
    console.print("[bold][[y][/bold] Continue   [bold][[n/q][/bold] Quit")
    while True:
        key = input("> ").strip().lower()
        if key in ("", "y", "yes"):
            return True
        if key in ("n", "q", "no", "quit"):
            return False


def _produce_section(
    section: dict,
    project: Project,
    redo: bool,
    progress: Progress,
    style_id: str | None = None,
) -> Path | None:
    sid = section["id"]
    sec_dir = project.section_dir(sid)
    section_mp4 = sec_dir / "section.mp4"

    if not redo and section_mp4.exists():
        progress(f"section {sid} already done — skipping")
        return section_mp4

    # Clear prior artifacts if redo
    if redo:
        for f in sec_dir.iterdir():
            if f.is_file():
                f.unlink()

    scenes = section.get("scenes", [])
    w, h = project.res_wh
    voice_id = project.voice_id

    # ── 3a: Images ──────────────────────────────────────────────────────
    progress(f"[{sid}] generating {len(scenes)} image(s)")
    for sc in scenes:
        img_path = sec_dir / f"scene_{sc['idx']:04d}.png"
        prompt = sc.get("image_prompt") or sc.get("vo") or "cinematic still"
        try:
            image_gen.render(prompt, img_path, style_id=style_id)
        except Exception as e:  # noqa: BLE001
            progress(f"  image {sc['idx']} failed: {e}")

    # ── 3b: VO ──────────────────────────────────────────────────────────
    progress(f"[{sid}] generating VO")
    durations: dict[int, float] = {}
    for sc in scenes:
        vo_text = sc.get("vo") or ""
        if not vo_text.strip():
            durations[sc["idx"]] = 3.0
            continue
        mp3_path = sec_dir / f"scene_{sc['idx']:04d}_vo.mp3"
        try:
            dur = vo_gen.render(vo_text, voice_id, mp3_path)
            durations[sc["idx"]] = dur
        except Exception as e:  # noqa: BLE001
            progress(f"  VO {sc['idx']} failed: {e}")
            durations[sc["idx"]] = 4.0

    # ── 3c: Ken Burns clips ─────────────────────────────────────────────
    progress(f"[{sid}] rendering Ken Burns clips")
    scene_clips: list[Path] = []
    for sc in scenes:
        img_path = sec_dir / f"scene_{sc['idx']:04d}.png"
        mp3_path = sec_dir / f"scene_{sc['idx']:04d}_vo.mp3"
        clip_path = sec_dir / f"scene_{sc['idx']:04d}.mp4"
        dur = durations.get(sc["idx"], 4.0)
        move = sc.get("camera_move") or "static"

        if not img_path.exists():
            progress(f"  missing image for scene {sc['idx']} — skipping clip")
            continue
        if not mp3_path.exists():
            progress(f"  missing VO for scene {sc['idx']} — skipping clip")
            continue
        try:
            kenburns.render(
                image_path=img_path,
                vo_path=mp3_path,
                out_path=clip_path,
                duration_s=dur,
                camera_move=move,
                width=w,
                height=h,
            )
            scene_clips.append(clip_path)
        except Exception as e:  # noqa: BLE001
            progress(f"  clip {sc['idx']} render failed: {e}")

    if not scene_clips:
        progress(f"[{sid}] no clips produced — skipping section")
        return None

    # ── 3d: Review gate ─────────────────────────────────────────────────
    images = [sec_dir / f"scene_{sc['idx']:04d}.png" for sc in scenes
              if (sec_dir / f"scene_{sc['idx']:04d}.png").exists()]
    audios = [sec_dir / f"scene_{sc['idx']:04d}_vo.mp3" for sc in scenes
              if (sec_dir / f"scene_{sc['idx']:04d}_vo.mp3").exists()]

    decision = gate.review(sid, images, audios)
    if decision == "quit":
        raise SystemExit(0)
    if decision == "redo":
        return _produce_section(section, project, redo=True, progress=progress)

    # ── Section assembly ─────────────────────────────────────────────────
    progress(f"[{sid}] assembling section")
    assembler.assemble_section(scene_clips, section_mp4)
    project.set_section_status(sid, "approved")
    return section_mp4


def produce_section_for_web(
    project: Project,
    section: dict,
    redo: bool = False,
    progress: Progress = print,
    style_id: str | None = None,
) -> "Path | None":
    """Produce a single section without a CLI gate — designed for web/API use.

    Patches the gate to auto-approve, calls _produce_section, then restores
    the original gate so CLI usage is unaffected.
    """
    import core.produce.gate as _gate
    original_review = _gate.review
    _gate.review = lambda sid, imgs, auds: "approve"  # noqa: E731
    try:
        return _produce_section(section, project, redo=redo, progress=progress, style_id=style_id)
    finally:
        _gate.review = original_review


def produce(
    blueprint_path: Path,
    name: str,
    topic: str,
    resolution: str = "2K",
    duration_hint: str = "10min",
    voice_id: str | None = None,
    redo_section: str | None = None,
    no_gate: bool = False,
    music_path: Path | None = None,
    thumbnail_channel: str | None = None,
    style_id: str | None = None,
    progress: Progress = print,
) -> Path:
    """Run the full production pipeline. Returns path to final MP4."""

    # ── Load blueprint ───────────────────────────────────────────────────
    blueprint = json.loads(blueprint_path.read_text(encoding="utf-8"))
    project = Project(name)

    # ── Voice selection ──────────────────────────────────────────────────
    from cli import config as cfg
    resolved_voice = (
        voice_id
        or project.get("voice_id")
        or cfg.get("elevenlabs.default_voice_id")
    )
    if not resolved_voice:
        from core.produce.elevenlabs import pick_voice_interactive
        resolved_voice = pick_voice_interactive()

    # ── Init project ─────────────────────────────────────────────────────
    if not project.get("blueprint_path"):
        project.init(
            blueprint_path=str(blueprint_path),
            topic=topic,
            resolution=resolution,
            voice_id=resolved_voice,
            duration_hint=duration_hint,
        )
    else:
        project.set("voice_id", resolved_voice)

    # Persist thumbnail_channel so re-runs don't need to re-specify it.
    resolved_thumbnail_channel: str | None = (
        thumbnail_channel or project.get("thumbnail_channel") or None
    )
    if thumbnail_channel and not project.get("thumbnail_channel"):
        project.set("thumbnail_channel", thumbnail_channel)

    # ── Stage 1: Script generation ───────────────────────────────────────
    if not project.script_path.exists():
        progress("generating script (claude)…")
        script = script_gen.generate(blueprint, topic, duration_hint)
        project.script_path.write_text(
            json.dumps(script, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    else:
        script = json.loads(project.script_path.read_text(encoding="utf-8"))

    # ── Stage 2: Section confirmation ────────────────────────────────────
    confirmed = project.get("sections_confirmed")
    if not confirmed:
        if not _confirm_sections(script):
            console.print("[yellow]Aborted. Edit script.json then re-run.[/]")
            raise SystemExit(0)
        project.set("sections_confirmed", True)

    # ── Stage 3: Per-section production ─────────────────────────────────
    section_videos: list[Path] = []
    for section in script.get("sections", []):
        sid = section["id"]
        force_redo = (redo_section == sid)
        sec_mp4 = project.section_dir(sid) / "section.mp4"

        if no_gate:
            # Patch gate to auto-approve
            import core.produce.gate as _gate
            _gate.review = lambda sid, imgs, auds: "approve"  # noqa: E731

        mp4 = _produce_section(section, project, redo=force_redo, progress=progress, style_id=style_id)
        if mp4:
            section_videos.append(mp4)

    # ── Stage 4: Final assembly ──────────────────────────────────────────
    progress("assembling final video…")
    music = music_path or project.music_path
    final = assembler.assemble_final(section_videos, project.final_output(), music)
    progress(f"done → {final}")

    # ── DB indexing ──────────────────────────────────────────────────────
    try:
        import datetime as dt
        from data.db import db
        d = db()
        if "productions" in d.table_names():
            d["productions"].upsert({
                "name": name,
                "blueprint_path": str(blueprint_path),
                "topic": topic,
                "resolution": resolution,
                "voice_id": resolved_voice,
                "section_count": len(script.get("sections", [])),
                "status": "done",
                "created_at": dt.datetime.now(dt.UTC).isoformat(),
            }, pk="name", alter=True)
    except Exception:  # noqa: BLE001
        pass

    # ── Stage 5: Thumbnail generation ───────────────────────────────────
    # Runs last so the video is fully assembled before any image API quota
    # is spent on thumbnail work. Non-fatal — a failure here never aborts
    # the already-finished video.
    if resolved_thumbnail_channel:
        progress(f"generating thumbnail for '{topic}' (@{resolved_thumbnail_channel})…")
        try:
            from generators.pipeline import run_pipeline as _run_thumb
            thumb_result = _run_thumb(
                title=topic,
                channel=resolved_thumbnail_channel,
                variants=1,
                do_quality=True,
                out_root=project.output_dir,
                on_progress=progress,
            )
            progress(f"thumbnail done → {thumb_result.output_dir}")
        except Exception as e:  # noqa: BLE001
            progress(f"thumbnail generation skipped: {e}")
    else:
        progress("no --thumbnail-channel provided — skipping thumbnail generation")

    return final
