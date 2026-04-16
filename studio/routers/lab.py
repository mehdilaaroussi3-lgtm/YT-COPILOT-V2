"""The Lab — single-video reverse-engineer → produce pipeline."""
from __future__ import annotations

import datetime as dt
import json
import re
import threading
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from cli import config as cfg

router = APIRouter()

# ── Storage roots ─────────────────────────────────────────────────────────────
LAB_DIR = Path("data/lab")
LAB_DIR.mkdir(parents=True, exist_ok=True)

PROD_ROOT = Path("data/productions")
PROD_ROOT.mkdir(parents=True, exist_ok=True)


def _sdir(sid: str) -> Path:
    d = LAB_DIR / sid
    d.mkdir(parents=True, exist_ok=True)
    return d


def _load(sid: str) -> dict:
    p = LAB_DIR / sid / "session.json"
    if not p.exists():
        raise HTTPException(404, f"Session {sid!r} not found")
    return json.loads(p.read_text("utf-8"))


def _save(sid: str, data: dict) -> None:
    (LAB_DIR / sid / "session.json").write_text(
        json.dumps(data, indent=2, ensure_ascii=False), "utf-8"
    )


def _blueprint(sid: str) -> dict:
    p = LAB_DIR / sid / "blueprint.json"
    if not p.exists():
        raise HTTPException(400, "Blueprint not ready for this session")
    return json.loads(p.read_text("utf-8"))


# ── In-memory job tracking ────────────────────────────────────────────────────
_reverse_jobs:    dict[str, dict] = {}
_idea_jobs:       dict[str, dict] = {}
_script_jobs:     dict[str, dict] = {}
_section_jobs:    dict[str, dict] = {}   # key: "{sid}:{section_id}"
_image_jobs:      dict[str, dict] = {}   # key: "{sid}:{section_id}"
_vo_jobs:         dict[str, dict] = {}   # key: session_id
_all_image_jobs:  dict[str, dict] = {}   # key: session_id
_final_jobs:      dict[str, dict] = {}   # key: session_id
_thumb_jobs:      dict[str, dict] = {}

# ── Cancellation flags — threading.Event per active job ──────────────────────
# Keys: sid (voiceover), "images:{sid}" (image gen), "{sid}:{section_id}" (section)
_cancel_flags: dict[str, threading.Event] = {}


# ── Blueprint summary ─────────────────────────────────────────────────────────
def _summary(bp: dict) -> dict:
    src = bp.get("source", {})
    pf  = bp.get("production_formula", {})
    sf  = bp.get("script_formula", {})
    vf  = bp.get("visual_style_formula", {})
    pt  = bp.get("pacing_template", {})
    rec = bp.get("recommendation", {})
    return {
        "title":              src.get("title", ""),
        "channel":            src.get("channel", ""),
        "duration_s":         src.get("duration_s", 0),
        "production_type":    pf.get("primary", ""),
        "confidence":         round(pf.get("confidence", 0) * 100),
        "hook_pattern":       sf.get("hook_pattern", ""),
        "tone":               sf.get("tone", []),
        "vo_style":           sf.get("vo_style", ""),
        "visual_mood":        vf.get("visual_mood", ""),
        "style_tags":         vf.get("style_tags", [])[:8],
        "scene_count":        len(bp.get("scene_prompts", [])),
        "avg_scene_s":        round(pt.get("avg_scene_length_s", 0), 1),
        "must_keep":          rec.get("must_keep", []),
        "narrative_arc":      sf.get("narrative_arc", []),
        "image_prompt_prefix": vf.get("image_prompt_prefix", ""),
        "hook_text":          sf.get("hook_text", ""),
        "reproducibility":    rec.get("when_reproducing", ""),
    }


# ── VOICES ────────────────────────────────────────────────────────────────────
VOICES = [
    {"id": "21m00Tcm4TlvDq8ikWAM", "name": "Rachel",  "accent": "American", "gender": "F", "style": "Calm, narrative"},
    {"id": "AZnzlk1XvdvUeBnXmlld", "name": "Domi",    "accent": "American", "gender": "F", "style": "Strong, expressive"},
    {"id": "EXAVITQu4vr4xnSDxMaL", "name": "Bella",   "accent": "American", "gender": "F", "style": "Soft, documentary"},
    {"id": "ErXwobaYiN019PkySvjV",  "name": "Antoni",  "accent": "American", "gender": "M", "style": "Well-rounded"},
    {"id": "MF3mGyEYCl7XYWbV9V6O", "name": "Elli",    "accent": "American", "gender": "F", "style": "Emotional, young"},
    {"id": "TxGEqnHWrfWFTfGW9XjX", "name": "Josh",    "accent": "American", "gender": "M", "style": "Deep, storytelling"},
    {"id": "VR6AewLTigWG4xSOukaG", "name": "Arnold",  "accent": "American", "gender": "M", "style": "Crisp, commanding"},
    {"id": "pNInz6obpgDQGcFmaJgB", "name": "Adam",    "accent": "American", "gender": "M", "style": "Deep, narrative"},
    {"id": "yoZ06aMxZJJ28mfd3POQ", "name": "Sam",     "accent": "American", "gender": "M", "style": "Raspy, energetic"},
    {"id": "onwK4e9ZLuTAKqWW03F9", "name": "Daniel",  "accent": "British",  "gender": "M", "style": "Deep, authoritative"},
    {"id": "g5CIjZEefAph4nQFvHAz", "name": "Ethan",   "accent": "American", "gender": "M", "style": "Soft, ASMR-style"},
]


# ── Archive helper ────────────────────────────────────────────────────────────
def _archive_generation(sid: str, job_type: str, reason: str,
                         scenes_done: int = 0, scenes_total: int = 0,
                         error: str | None = None) -> None:
    """Append an archive entry so every generation (success, error, cancel) is logged."""
    try:
        from core.produce.project import Project
        proj = Project(sid)
        archive_path = proj.root / "generation_archive.jsonl"
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "archived_at": dt.datetime.now(dt.UTC).isoformat(),
            "job_type":    job_type,
            "reason":      reason,
            "scenes_done": scenes_done,
            "scenes_total": scenes_total,
            "error":       error,
            # snapshot counts of artefacts on disk at this moment
            "images_on_disk": len(list(proj.root.rglob("*.png"))),
            "mp3s_on_disk":   len(list(proj.root.rglob("*.mp3"))),
        }
        with archive_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")
    except Exception:
        pass  # never let archiving crash the caller


# ── Cancel active generations ─────────────────────────────────────────────────
@router.post("/api/lab/{sid}/cancel")
def cancel_generation(sid: str):
    """Signal all running jobs for this session to stop at the next checkpoint."""
    cancelled = []
    keys_to_cancel = [sid, f"images:{sid}"]
    # also catch any section jobs
    keys_to_cancel += [k for k in _cancel_flags if k.startswith(f"{sid}:")]
    for key in keys_to_cancel:
        flag = _cancel_flags.get(key)
        if flag and not flag.is_set():
            flag.set()
            cancelled.append(key)
    return {"ok": True, "cancelled": cancelled}


@router.get("/api/lab/voices")
def get_voices():
    # Try to fetch live from ElevenLabs to get preview_url
    try:
        from core.produce.elevenlabs import list_voices as _list
        live = _list()
        # Merge with VOICES fallback to keep our curated labels
        id_to_static = {v["id"]: v for v in VOICES}
        items = []
        for v in live:
            static = id_to_static.get(v["id"], {})
            items.append({
                "id": v["id"],
                "name": v["name"],
                "accent": static.get("accent") or v["labels"].get("accent", ""),
                "gender": static.get("gender") or ("F" if v["labels"].get("gender") == "female" else "M"),
                "style": static.get("style") or v["labels"].get("use case") or v["labels"].get("description") or "",
                "preview_url": v.get("preview_url") or "",
            })
        if items:
            return {"items": items}
    except Exception:
        pass
    # Fallback: hardcoded list (no preview_url)
    return {"items": [dict(v, preview_url="") for v in VOICES]}


# ── SESSIONS ──────────────────────────────────────────────────────────────────
@router.get("/api/lab/sessions")
def list_sessions():
    items = []
    if LAB_DIR.exists():
        dirs = sorted(LAB_DIR.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
        for d in dirs:
            sp = d / "session.json"
            if sp.exists():
                try:
                    items.append(json.loads(sp.read_text("utf-8")))
                except Exception:
                    pass
    return {"items": items[:30]}


@router.get("/api/lab/sessions/{sid}")
def get_session(sid: str):
    s = _load(sid)
    bp_path = LAB_DIR / sid / "blueprint.json"
    if bp_path.exists():
        try:
            s["summary"] = _summary(json.loads(bp_path.read_text("utf-8")))
        except Exception:
            pass
    return s


@router.delete("/api/lab/sessions/{sid}")
def delete_session(sid: str):
    import shutil
    d = LAB_DIR / sid
    if d.exists():
        shutil.rmtree(d)
    prod = PROD_ROOT / sid
    if prod.exists():
        shutil.rmtree(prod)
    return {"ok": True}


# ── REVERSE ───────────────────────────────────────────────────────────────────
class ReverseRequest(BaseModel):
    url: str
    session_id: str | None = None


@router.post("/api/lab/reverse")
def start_reverse(req: ReverseRequest):
    from core.reverse import reverse as ure_reverse

    url = req.url.strip()
    if not url:
        raise HTTPException(400, "URL is required")

    sid = req.session_id or uuid.uuid4().hex[:12]
    _sdir(sid)

    job_id = uuid.uuid4().hex[:12]
    _reverse_jobs[job_id] = {
        "status": "running",
        "stages": [],
        "stage_current": "",
        "error": None,
        "session_id": sid,
        "summary": None,
    }

    def run():
        def progress(msg: str):
            _reverse_jobs[job_id]["stage_current"] = msg
            _reverse_jobs[job_id]["stages"].append(msg)

        try:
            out_dir: Path = ure_reverse(url, progress=progress)
            src_bp = out_dir / "blueprint.json"
            dst_bp = LAB_DIR / sid / "blueprint.json"
            dst_bp.write_bytes(src_bp.read_bytes())

            # Copy keyframes for preview
            frames_src = out_dir / "frames"
            frames_dst = LAB_DIR / sid / "frames"
            if frames_src.exists() and not frames_dst.exists():
                import shutil
                shutil.copytree(frames_src, frames_dst)

            bp = json.loads(dst_bp.read_text("utf-8"))
            sm = _summary(bp)

            now = dt.datetime.now(dt.UTC).isoformat()
            session = {
                "id": sid,
                "url": url,
                "yt_title": sm["title"],
                "yt_channel": sm["channel"],
                "step": "reverse_done",
                "idea": None,
                "voice_id": cfg.get("elevenlabs.default_voice_id", ""),
                "duration_min": 5,
                "style_id": None,
                "created_at": now,
                "updated_at": now,
            }
            _save(sid, session)

            _reverse_jobs[job_id]["status"] = "done"
            _reverse_jobs[job_id]["summary"] = sm
        except Exception as e:
            _reverse_jobs[job_id]["status"] = "error"
            _reverse_jobs[job_id]["error"] = str(e)
            import traceback
            traceback.print_exc()

    threading.Thread(target=run, daemon=True).start()
    return {"job_id": job_id, "session_id": sid}


@router.get("/api/lab/reverse/{job_id}/status")
def reverse_status(job_id: str):
    job = _reverse_jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Reverse job not found")
    return job


# ── STYLE SELECTION ───────────────────────────────────────────────────────────
class StyleSelectRequest(BaseModel):
    session_id: str
    style_id: str | None = None


@router.post("/api/lab/style")
def set_style(req: StyleSelectRequest):
    """Set the style_id for a lab session."""
    s = _load(req.session_id)
    s["style_id"] = req.style_id
    s["updated_at"] = dt.datetime.now(dt.UTC).isoformat()
    _save(req.session_id, s)
    return {"ok": True}


# ── IDEAS ─────────────────────────────────────────────────────────────────────
class IdeasRequest(BaseModel):
    session_id: str
    topic: str | None = None
    count: int = 6


@router.post("/api/lab/ideas")
def start_ideas(req: IdeasRequest):
    from generators.gemini_text import generate_text

    bp = _blueprint(req.session_id)
    sf  = bp.get("script_formula", {})
    vf  = bp.get("visual_style_formula", {})
    src = bp.get("source", {})

    job_id = uuid.uuid4().hex[:12]
    _idea_jobs[job_id] = {"status": "running", "items": [], "error": None}

    topic_block = f'\nThe user wants videos about: "{req.topic}"\n' if req.topic else ""

    prompt = f"""You are a YouTube video strategist.

I reverse-engineered a video from @{src.get("channel", "unknown")} and extracted its full production formula:

HOOK PATTERN: {sf.get("hook_pattern", "")}
HOOK EXAMPLE: {sf.get("hook_text", "")}
NARRATIVE ARC: {", ".join(sf.get("narrative_arc", []))}
TONE: {", ".join(sf.get("tone", []))}
VO STYLE: {sf.get("vo_style", "")}
VISUAL MOOD: {vf.get("visual_mood", "")}
STYLE TAGS: {", ".join(vf.get("style_tags", [])[:8])}
{topic_block}
Generate {req.count} compelling YouTube video ideas that would work PERFECTLY in this formula.
Each idea must:
- Fit the hook pattern and narrative arc above
- Match the tone and VO style
- Have a strong curiosity gap
- Be clearly distinct from the others

Output STRICT JSON only — array of {req.count} objects:
[{{"title": "...", "description": "1-2 sentences on what the video covers", "angle": "why this idea fits this formula"}}]
No prose, no markdown fence."""

    def run():
        try:
            from core.idea_generator import _parse_json_array
            raw = generate_text(prompt, temperature=0.9)
            items = _parse_json_array(raw)
            _idea_jobs[job_id]["items"] = items[:req.count]
            _idea_jobs[job_id]["status"] = "done"
        except Exception as e:
            _idea_jobs[job_id]["status"] = "error"
            _idea_jobs[job_id]["error"] = str(e)

    threading.Thread(target=run, daemon=True).start()
    return {"job_id": job_id}


@router.get("/api/lab/ideas/{job_id}")
def ideas_status(job_id: str):
    job = _idea_jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Ideas job not found")
    return job


# ── IDEA SELECTION ────────────────────────────────────────────────────────────
class IdeaSelectRequest(BaseModel):
    session_id: str
    idea: str


@router.post("/api/lab/idea/select")
def select_idea(req: IdeaSelectRequest):
    s = _load(req.session_id)
    s["idea"] = req.idea
    s["step"] = "idea_done"
    s["updated_at"] = dt.datetime.now(dt.UTC).isoformat()
    _save(req.session_id, s)
    return {"ok": True}


# ── VOICE SELECTION ───────────────────────────────────────────────────────────
class VoiceRequest(BaseModel):
    session_id: str
    voice_id: str


@router.post("/api/lab/voice")
def set_voice(req: VoiceRequest):
    s = _load(req.session_id)
    s["voice_id"] = req.voice_id
    s["step"] = "voice_done"
    s["updated_at"] = dt.datetime.now(dt.UTC).isoformat()
    _save(req.session_id, s)
    return {"ok": True}


# ── SCRIPT GENERATION ─────────────────────────────────────────────────────────
class ScriptStartRequest(BaseModel):
    session_id: str
    duration_min: int = 5


@router.post("/api/lab/script")
def start_script(req: ScriptStartRequest):
    from core.produce.script_gen import generate as gen_script
    from core.produce.project import Project

    s = _load(req.session_id)
    if not s.get("idea"):
        raise HTTPException(400, "No idea selected — complete the Ideas step first")

    bp = _blueprint(req.session_id)
    topic = s["idea"]
    duration_hint = f"{req.duration_min}min"
    voice_id = s.get("voice_id") or cfg.get("elevenlabs.default_voice_id", "")

    s["duration_min"] = req.duration_min
    s["step"] = "script_generating"
    s["updated_at"] = dt.datetime.now(dt.UTC).isoformat()
    _save(req.session_id, s)

    job_id = uuid.uuid4().hex[:12]
    _script_jobs[job_id] = {"status": "running", "error": None}

    def run():
        try:
            script = gen_script(bp, topic, duration_hint)

            # Initialise the produce Project so script.json is at the right path
            proj = Project(req.session_id)
            proj.init(
                blueprint_path=str(LAB_DIR / req.session_id / "blueprint.json"),
                topic=topic,
                resolution="4K",
                voice_id=voice_id,
                duration_hint=duration_hint,
            )
            proj.script_path.write_text(
                json.dumps(script, indent=2, ensure_ascii=False), "utf-8"
            )
            for sec in script.get("sections", []):
                proj.set_section_status(sec["id"], "pending")

            fresh = _load(req.session_id)
            fresh["step"] = "script_done"
            fresh["updated_at"] = dt.datetime.now(dt.UTC).isoformat()
            _save(req.session_id, fresh)

            _script_jobs[job_id]["status"] = "done"
        except Exception as e:
            _script_jobs[job_id]["status"] = "error"
            _script_jobs[job_id]["error"] = str(e)
            import traceback
            traceback.print_exc()

    threading.Thread(target=run, daemon=True).start()
    return {"job_id": job_id}


@router.get("/api/lab/script/{job_id}/status")
def script_job_status(job_id: str):
    job = _script_jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Script job not found")
    return job


@router.get("/api/lab/{sid}/script")
def get_script(sid: str):
    from core.produce.project import Project
    proj = Project(sid)
    if not proj.script_path.exists():
        raise HTTPException(404, "Script not ready")
    return json.loads(proj.script_path.read_text("utf-8"))


class ScriptSave(BaseModel):
    script_json: str


@router.post("/api/lab/{sid}/script/save")
def save_script(sid: str, body: ScriptSave):
    from core.produce.project import Project
    proj = Project(sid)
    proj.script_path.write_text(body.script_json, "utf-8")
    s = _load(sid)
    s["step"] = "script_done"
    _save(sid, s)
    return {"ok": True}


@router.post("/api/lab/{sid}/script/approve")
def approve_script(sid: str):
    s = _load(sid)
    s["step"] = "script_approved"
    s["updated_at"] = dt.datetime.now(dt.UTC).isoformat()
    _save(sid, s)
    return {"ok": True}


# ── SECTIONS ──────────────────────────────────────────────────────────────────
@router.get("/api/lab/{sid}/sections")
def get_sections(sid: str):
    from core.produce.project import Project
    proj = Project(sid)
    if not proj.script_path.exists():
        return {"items": []}
    script = json.loads(proj.script_path.read_text("utf-8"))
    items = []
    for sec in script.get("sections", []):
        section_id = sec["id"]
        db_status = proj.section_status(section_id)
        mp4 = proj.section_dir(section_id) / "section.mp4"
        job = _section_jobs.get(f"{sid}:{section_id}", {})
        items.append({
            "id":          section_id,
            "label":       sec.get("label", section_id),
            "scene_count": len(sec.get("scenes", [])),
            "status":      job.get("status") or db_status or "pending",
            "current":     job.get("current", ""),
            "error":       job.get("error"),
            "mp4_url":     f"/productions/{sid}/sections/{section_id}/section.mp4" if mp4.exists() else None,
        })
    return {"items": items, "title_suggestion": script.get("title_suggestion", "")}


class SectionRequest(BaseModel):
    feedback: str | None = None


@router.post("/api/lab/{sid}/section/{section_id}/produce")
def produce_section(sid: str, section_id: str, req: SectionRequest):
    from core.produce.project import Project
    from core.produce.pipeline import produce_section_for_web

    job_key = f"{sid}:{section_id}"
    _section_jobs[job_key] = {
        "status": "running",
        "current": "Preparing…",
        "error": None,
        "mp4_url": None,
    }

    def run():
        try:
            s = _load(sid)
            proj = Project(sid)
            script = json.loads(proj.script_path.read_text("utf-8"))
            section = next(
                (s for s in script["sections"] if s["id"] == section_id), None
            )
            if section is None:
                raise ValueError(f"Section '{section_id}' not found in script")

            # Apply feedback before producing
            if req.feedback:
                section = _apply_feedback(section_id, req.feedback, script, proj)

            def progress(msg: str):
                _section_jobs[job_key]["current"] = msg

            redo = bool(req.feedback)
            style_id = s.get("style_id")
            produce_section_for_web(proj, section, redo=redo, progress=progress, style_id=style_id)

            mp4 = proj.section_dir(section_id) / "section.mp4"
            proj.set_section_status(section_id, "done")
            _section_jobs[job_key]["status"] = "done"
            _section_jobs[job_key]["mp4_url"] = (
                f"/productions/{sid}/sections/{section_id}/section.mp4"
                if mp4.exists() else None
            )
        except Exception as e:
            _section_jobs[job_key]["status"] = "error"
            _section_jobs[job_key]["error"] = str(e)
            import traceback
            traceback.print_exc()

    threading.Thread(target=run, daemon=True).start()
    return {"ok": True}


@router.get("/api/lab/{sid}/section/{section_id}/status")
def section_status(sid: str, section_id: str):
    job = _section_jobs.get(f"{sid}:{section_id}", {})
    if not job:
        return {"status": "pending"}
    return job


def _apply_feedback(section_id: str, feedback: str, script: dict, proj) -> dict:
    """Ask Claude to update a section's script based on user feedback. Returns updated section."""
    from generators.gemini_text import generate_text

    section = next((s for s in script["sections"] if s["id"] == section_id), None)
    if not section:
        return section

    prompt = f"""You are editing one section of a YouTube narration script based on user feedback.

CURRENT SECTION ({section.get("label", section_id)}):
{json.dumps(section, indent=2, ensure_ascii=False)}

USER FEEDBACK:
{feedback}

Apply the feedback. Keep the exact JSON structure. Update VO text, image_prompt, camera_move, or on_screen_text as needed.
Return ONLY the updated section JSON object — no prose, no markdown fence."""

    try:
        raw = generate_text(prompt, temperature=0.45).strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        updated = json.loads(raw)
        # Persist updated script
        for i, s in enumerate(script["sections"]):
            if s["id"] == section_id:
                script["sections"][i] = updated
                break
        proj.script_path.write_text(json.dumps(script, indent=2, ensure_ascii=False), "utf-8")
        return updated
    except Exception:
        return section  # keep original on parse failure


# ── VOICEOVER GENERATION (all scenes, full preview) ──────────────────────────
def _concat_mp3(files: list[Path], out: Path) -> None:
    """Binary-concatenate MP3 files into one preview file."""
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "wb") as fout:
        for f in files:
            if f.exists():
                fout.write(f.read_bytes())


@router.post("/api/lab/{sid}/voiceover")
def start_voiceover(sid: str):
    from core.produce.project import Project
    from core.produce import vo_gen

    s = _load(sid)
    voice_id = s.get("voice_id") or ""
    if not voice_id:
        raise HTTPException(400, "No voice selected")

    cancel_flag = threading.Event()
    _cancel_flags[sid] = cancel_flag

    _vo_jobs[sid] = {
        "status": "running", "scenes_done": 0, "scenes_total": 0,
        "preview_url": None, "word_count": 0, "scene_durations": {}, "error": None,
    }

    def run():
        try:
            proj = Project(sid)
            if not proj.script_path.exists():
                raise RuntimeError("Script not found")
            script = json.loads(proj.script_path.read_text("utf-8"))

            # Wipe stale preview so the old audio never gets served mid-run
            preview_path = proj.root / "voiceover_preview.mp3"
            if preview_path.exists():
                preview_path.unlink()

            all_scenes: list[tuple[str, dict]] = []
            all_vo_text: list[str] = []
            for sec in script.get("sections", []):
                for sc in sec.get("scenes", []):
                    all_scenes.append((sec["id"], sc))
                    if sc.get("vo"):
                        all_vo_text.append(sc["vo"])

            _vo_jobs[sid]["scenes_total"] = len(all_scenes)
            _vo_jobs[sid]["word_count"] = len(" ".join(all_vo_text).split())

            mp3_files: list[Path] = []
            durations: dict[str, float] = {}

            for sec_id, sc in all_scenes:
                # ── Check cancel between every scene ──────────────────────
                if cancel_flag.is_set():
                    scenes_done = _vo_jobs[sid]["scenes_done"]
                    _vo_jobs[sid]["status"] = "cancelled"
                    _archive_generation(sid, "voiceover", "cancelled",
                                        scenes_done=scenes_done,
                                        scenes_total=len(all_scenes))
                    return

                sec_dir = proj.section_dir(sec_id)
                mp3_path = sec_dir / f"scene_{sc['idx']:04d}_vo.mp3"
                vo_text = sc.get("vo") or ""
                key = f"{sec_id}:{sc['idx']}"
                if vo_text.strip():
                    dur = vo_gen.render(vo_text, voice_id, mp3_path, force=True)
                    durations[key] = round(dur, 3)
                    mp3_files.append(mp3_path)
                else:
                    durations[key] = 0.0
                _vo_jobs[sid]["scenes_done"] += 1

            # Concatenate for preview
            preview_path = proj.root / "voiceover_preview.mp3"
            _concat_mp3(mp3_files, preview_path)

            _vo_jobs[sid].update({
                "status": "done",
                "preview_url": f"/productions/{sid}/voiceover_preview.mp3",
                "scene_durations": durations,
            })

            # Persist durations to disk
            (proj.root / "vo_durations.json").write_text(
                json.dumps(durations, ensure_ascii=False), "utf-8"
            )

            _archive_generation(sid, "voiceover", "completed",
                                 scenes_done=len(all_scenes),
                                 scenes_total=len(all_scenes))

            s2 = _load(sid)
            s2["step"] = "voiceover_done"
            s2["updated_at"] = dt.datetime.now(dt.UTC).isoformat()
            _save(sid, s2)

        except Exception as e:
            _vo_jobs[sid]["status"] = "error"
            _vo_jobs[sid]["error"] = str(e)
            _archive_generation(sid, "voiceover", "error",
                                 scenes_done=_vo_jobs[sid].get("scenes_done", 0),
                                 scenes_total=_vo_jobs[sid].get("scenes_total", 0),
                                 error=str(e))
            import traceback
            traceback.print_exc()
        finally:
            _cancel_flags.pop(sid, None)

    threading.Thread(target=run, daemon=True).start()
    return {"ok": True}


@router.get("/api/lab/{sid}/voiceover/status")
def voiceover_status(sid: str):
    job = _vo_jobs.get(sid)
    if not job:
        # Check if already done from a previous run
        try:
            proj = __import__("core.produce.project", fromlist=["Project"]).Project(sid)
            dur_path = proj.root / "vo_durations.json"
            preview_path = proj.root / "voiceover_preview.mp3"
            if dur_path.exists() and preview_path.exists():
                durations = json.loads(dur_path.read_text("utf-8"))
                return {
                    "status": "done",
                    "scenes_done": len(durations),
                    "scenes_total": len(durations),
                    "preview_url": f"/productions/{sid}/voiceover_preview.mp3",
                    "scene_durations": durations,
                    "word_count": 0,
                    "error": None,
                }
        except Exception:
            pass
        return {"status": "idle", "scenes_done": 0, "scenes_total": 0, "preview_url": None, "scene_durations": {}, "word_count": 0, "error": None}
    return job


# ── GLOBAL IMAGE GENERATION (all sections at once) ────────────────────────────
@router.post("/api/lab/{sid}/generate-images")
def generate_all_images(sid: str):
    from core.produce.project import Project
    from core.produce import image_gen

    img_cancel_flag = threading.Event()
    _cancel_flags[f"images:{sid}"] = img_cancel_flag

    _all_image_jobs[sid] = {
        "status": "running", "scene_statuses": {}, "image_urls": {}, "error": None,
    }

    def run():
        all_scenes_flat: list[tuple[dict, dict]] = []
        try:
            proj = Project(sid)
            script = json.loads(proj.script_path.read_text("utf-8"))

            # Build flat scene list for total count
            for sec in script.get("sections", []):
                for sc in sec.get("scenes", []):
                    all_scenes_flat.append((sec, sc))

            scenes_done = 0
            for sec, sc in all_scenes_flat:
                # ── Check cancel between every image ──────────────────────
                if img_cancel_flag.is_set():
                    _all_image_jobs[sid]["status"] = "cancelled"
                    _archive_generation(sid, "images", "cancelled",
                                        scenes_done=scenes_done,
                                        scenes_total=len(all_scenes_flat))
                    return

                idx = sc["idx"]
                key = f"{sec['id']}:{idx}"
                img_path = proj.section_dir(sec["id"]) / f"scene_{idx:04d}.png"
                if img_path.exists():
                    _all_image_jobs[sid]["scene_statuses"][key] = "done"
                    _all_image_jobs[sid]["image_urls"][key] = (
                        f"/productions/{sid}/sections/{sec['id']}/scene_{idx:04d}.png"
                    )
                    scenes_done += 1
                    continue
                _all_image_jobs[sid]["scene_statuses"][key] = "generating"
                prompt = sc.get("image_prompt") or sc.get("vo") or "cinematic still"
                try:
                    image_gen.render(prompt, img_path, force=True)
                    _all_image_jobs[sid]["scene_statuses"][key] = "done"
                    _all_image_jobs[sid]["image_urls"][key] = (
                        f"/productions/{sid}/sections/{sec['id']}/scene_{idx:04d}.png"
                    )
                except Exception as e:  # noqa: BLE001
                    _all_image_jobs[sid]["scene_statuses"][key] = f"error:{e}"
                scenes_done += 1

            _all_image_jobs[sid]["status"] = "done"
            _archive_generation(sid, "images", "completed",
                                 scenes_done=scenes_done,
                                 scenes_total=len(all_scenes_flat))

            s2 = _load(sid)
            s2["step"] = "visuals_done"
            s2["updated_at"] = dt.datetime.now(dt.UTC).isoformat()
            _save(sid, s2)
        except Exception as e:
            _all_image_jobs[sid]["status"] = "error"
            _all_image_jobs[sid]["error"] = str(e)
            _archive_generation(sid, "images", "error",
                                 scenes_done=sum(
                                     1 for v in _all_image_jobs[sid]["scene_statuses"].values()
                                     if v == "done"
                                 ),
                                 scenes_total=len(all_scenes_flat),
                                 error=str(e))
            import traceback
            traceback.print_exc()
        finally:
            _cancel_flags.pop(f"images:{sid}", None)

    threading.Thread(target=run, daemon=True).start()
    return {"ok": True}


@router.get("/api/lab/{sid}/images/status")
def all_images_status(sid: str):
    from core.produce.project import Project
    job = _all_image_jobs.get(sid, {"status": "idle", "scene_statuses": {}, "image_urls": {}})
    # Scan disk for existing images (supports page reload)
    try:
        proj = Project(sid)
        script = json.loads(proj.script_path.read_text("utf-8"))
        for sec in script.get("sections", []):
            for sc in sec.get("scenes", []):
                key = f"{sec['id']}:{sc['idx']}"
                img = proj.section_dir(sec["id"]) / f"scene_{sc['idx']:04d}.png"
                if img.exists() and key not in job.get("image_urls", {}):
                    job.setdefault("image_urls", {})[key] = (
                        f"/productions/{sid}/sections/{sec['id']}/scene_{sc['idx']:04d}.png"
                    )
                    job.setdefault("scene_statuses", {})[key] = "done"
    except Exception:
        pass
    return job


# ── PER-SECTION IMAGE GENERATION ─────────────────────────────────────────────
@router.post("/api/lab/{sid}/section/{section_id}/generate-images")
def generate_section_images(sid: str, section_id: str):
    from core.produce.project import Project
    from core.produce import image_gen

    job_key = f"{sid}:{section_id}:images"
    _image_jobs[job_key] = {"status": "running", "scene_statuses": {}, "error": None}

    def run():
        try:
            proj = Project(sid)
            if not proj.script_path.exists():
                raise RuntimeError("Script not found")
            script = json.loads(proj.script_path.read_text("utf-8"))
            section = next((s for s in script.get("sections", []) if s["id"] == section_id), None)
            if not section:
                raise RuntimeError(f"Section '{section_id}' not found")

            sec_dir = proj.section_dir(section_id)
            scenes = section.get("scenes", [])

            for sc in scenes:
                idx = sc["idx"]
                img_path = sec_dir / f"scene_{idx:04d}.png"
                if img_path.exists():
                    _image_jobs[job_key]["scene_statuses"][str(idx)] = "done"
                    continue
                _image_jobs[job_key]["scene_statuses"][str(idx)] = "generating"
                prompt = sc.get("image_prompt") or sc.get("vo") or "cinematic still"
                try:
                    image_gen.render(prompt, img_path)
                    _image_jobs[job_key]["scene_statuses"][str(idx)] = "done"
                except Exception as e:  # noqa: BLE001
                    _image_jobs[job_key]["scene_statuses"][str(idx)] = f"error:{e}"

            _image_jobs[job_key]["status"] = "done"
        except Exception as e:
            _image_jobs[job_key]["status"] = "error"
            _image_jobs[job_key]["error"] = str(e)
            import traceback
            traceback.print_exc()

    threading.Thread(target=run, daemon=True).start()
    return {"ok": True}


@router.get("/api/lab/{sid}/section/{section_id}/images/status")
def section_images_status(sid: str, section_id: str):
    from core.produce.project import Project
    job_key = f"{sid}:{section_id}:images"
    job = _image_jobs.get(job_key, {"status": "idle", "scene_statuses": {}})

    # Build image URLs for scenes that have files on disk
    image_urls: dict[str, str] = {}
    try:
        proj = Project(sid)
        if proj.script_path.exists():
            script = json.loads(proj.script_path.read_text("utf-8"))
            section = next((s for s in script.get("sections", []) if s["id"] == section_id), None)
            if section:
                sec_dir = proj.section_dir(section_id)
                for sc in section.get("scenes", []):
                    img_path = sec_dir / f"scene_{sc['idx']:04d}.png"
                    if img_path.exists():
                        image_urls[str(sc["idx"])] = (
                            f"/productions/{sid}/sections/{section_id}/scene_{sc['idx']:04d}.png"
                        )
    except Exception:  # noqa: BLE001
        pass

    return {
        "status": job.get("status", "idle"),
        "scene_statuses": job.get("scene_statuses", {}),
        "image_urls": image_urls,
        "error": job.get("error"),
    }


# ── PER-SCENE IMAGE GENERATION ──────────────────────────────────────────────────
@router.post("/api/lab/{sid}/scene/{section_id}/{scene_idx}/generate-image")
def generate_scene_image(sid: str, section_id: str, scene_idx: int):
    """Generate image for a single scene. Skip if it already exists."""
    from core.produce.project import Project
    from core.produce import image_gen

    job_key = f"{sid}:{section_id}:{scene_idx}:image"
    _image_jobs[job_key] = {"status": "running", "error": None, "image_url": None}

    def run():
        try:
            proj = Project(sid)
            if not proj.script_path.exists():
                raise RuntimeError("Script not found")
            script = json.loads(proj.script_path.read_text("utf-8"))
            section = next((s for s in script.get("sections", []) if s["id"] == section_id), None)
            if not section:
                raise RuntimeError(f"Section '{section_id}' not found")

            scene = next((s for s in section.get("scenes", []) if s["idx"] == scene_idx), None)
            if not scene:
                raise RuntimeError(f"Scene {scene_idx} not found in section {section_id}")

            sec_dir = proj.section_dir(section_id)
            img_path = sec_dir / f"scene_{scene_idx:04d}.png"

            # Skip if already exists
            if img_path.exists():
                _image_jobs[job_key]["status"] = "done"
                _image_jobs[job_key]["image_url"] = (
                    f"/productions/{sid}/sections/{section_id}/scene_{scene_idx:04d}.png"
                )
                return

            prompt = scene.get("image_prompt") or scene.get("vo") or "cinematic still"
            image_gen.render(prompt, img_path)

            _image_jobs[job_key]["status"] = "done"
            _image_jobs[job_key]["image_url"] = (
                f"/productions/{sid}/sections/{section_id}/scene_{scene_idx:04d}.png"
            )
        except Exception as e:
            _image_jobs[job_key]["status"] = "error"
            _image_jobs[job_key]["error"] = str(e)
            import traceback
            traceback.print_exc()

    threading.Thread(target=run, daemon=True).start()
    return {"ok": True}


@router.get("/api/lab/{sid}/scene/{section_id}/{scene_idx}/image/status")
def scene_image_status(sid: str, section_id: str, scene_idx: int):
    """Check status of a single scene's image generation."""
    job_key = f"{sid}:{section_id}:{scene_idx}:image"
    job = _image_jobs.get(job_key, {"status": "idle", "error": None, "image_url": None})

    # Check disk for the file if status is idle
    if job.get("status") == "idle":
        try:
            proj = __import__("core.produce.project", fromlist=["Project"]).Project(sid)
            img_path = proj.section_dir(section_id) / f"scene_{scene_idx:04d}.png"
            if img_path.exists():
                return {
                    "status": "done",
                    "image_url": f"/productions/{sid}/sections/{section_id}/scene_{scene_idx:04d}.png",
                    "error": None,
                }
        except Exception:
            pass

    return job


# ── FINAL ASSEMBLY ────────────────────────────────────────────────────────────
@router.post("/api/lab/{sid}/assemble")
def start_assemble(sid: str):
    from core.produce.assembler import assemble_final
    from core.produce.project import Project

    job_id = f"assemble_{sid}"
    _final_jobs[job_id] = {"status": "running", "error": None, "mp4_url": None}

    def run():
        try:
            proj = Project(sid)
            script = json.loads(proj.script_path.read_text("utf-8"))
            clips = []
            for sec in script.get("sections", []):
                mp4 = proj.section_dir(sec["id"]) / "section.mp4"
                if mp4.exists():
                    clips.append(mp4)
            if not clips:
                raise RuntimeError("No section videos are ready to assemble")
            final = proj.final_output()
            assemble_final(clips, final, music_path=None)

            s = _load(sid)
            s["step"] = "assembled"
            s["updated_at"] = dt.datetime.now(dt.UTC).isoformat()
            _save(sid, s)

            _final_jobs[job_id]["status"] = "done"
            _final_jobs[job_id]["mp4_url"] = f"/productions/{sid}/output/final_4K.mp4"
        except Exception as e:
            _final_jobs[job_id]["status"] = "error"
            _final_jobs[job_id]["error"] = str(e)
            import traceback
            traceback.print_exc()

    threading.Thread(target=run, daemon=True).start()
    return {"ok": True}


@router.get("/api/lab/{sid}/assemble/status")
def assemble_status(sid: str):
    job = _final_jobs.get(f"assemble_{sid}", {})
    if not job:
        return {"status": "pending"}
    return job


# ── THUMBNAIL ─────────────────────────────────────────────────────────────────
class ThumbnailRequest(BaseModel):
    session_id: str
    channel_override: str | None = None
    variants: int = 1


@router.post("/api/lab/thumbnail")
def start_thumbnail(req: ThumbnailRequest):
    from generators.pipeline import run_pipeline

    s = _load(req.session_id)
    bp = _blueprint(req.session_id)
    title = s.get("idea") or bp.get("source", {}).get("title", "Untitled")
    channel = req.channel_override or bp.get("source", {}).get("channel", "")

    job_id = uuid.uuid4().hex[:12]
    _thumb_jobs[job_id] = {
        "status": "running",
        "current": "",
        "error": None,
        "variants": [],
    }

    out_root = LAB_DIR / req.session_id / "thumbnails"

    def run():
        try:
            def progress(msg: str):
                _thumb_jobs[job_id]["current"] = msg

            def on_variant(d: dict):
                if d.get("url"):
                    _thumb_jobs[job_id]["variants"].append(d["url"])

            run_pipeline(
                title=title,
                channel=channel,
                variants=req.variants,
                do_quality=False,
                on_progress=progress,
                on_variant_done=on_variant,
                out_root=out_root,
            )
            _thumb_jobs[job_id]["status"] = "done"
        except Exception as e:
            _thumb_jobs[job_id]["status"] = "error"
            _thumb_jobs[job_id]["error"] = str(e)

    threading.Thread(target=run, daemon=True).start()
    return {"job_id": job_id}


@router.get("/api/lab/thumbnail/{job_id}/status")
def thumbnail_status(job_id: str):
    job = _thumb_jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Thumbnail job not found")
    return job


# ── STATIC FILE SERVING ───────────────────────────────────────────────────────
@router.get("/productions/{name}/{rest:path}")
def serve_production(name: str, rest: str):
    p = PROD_ROOT / name / rest
    if not p.exists():
        raise HTTPException(404, "File not found")
    return FileResponse(str(p))


@router.get("/lab-files/{sid}/{rest:path}")
def serve_lab_files(sid: str, rest: str):
    p = LAB_DIR / sid / rest
    if not p.exists():
        raise HTTPException(404, "File not found")
    return FileResponse(str(p))


# ── TEMPLATE INTEGRATION ──────────────────────────────────────────────────────
class LabFromTemplateRequest(BaseModel):
    template_id: str
    topic: str = ""
    voice_id: str = ""


@router.post("/api/lab/from-template")
def lab_from_template(req: LabFromTemplateRequest):
    """Create a new lab session from a template instead of reversing a YouTube video.

    The template DNA is copied to the session's blueprint slot.
    Session starts at 'reverse_done' step (Ideas).
    """
    from data.db import db as get_db

    d = get_db()
    row = d["templates"].get(req.template_id)

    if not row:
        raise HTTPException(404, "Template not found")

    if row["status"] != "ready":
        raise HTTPException(400, f"Template not ready (status: {row['status']})")

    # Create new session
    sid = uuid.uuid4().hex[:12]
    sdir = _sdir(sid)

    # Copy template DNA → blueprint slot, inject source fields for _summary() compatibility
    dna_path = Path(row.get("dna_path", ""))
    if not dna_path.exists():
        raise HTTPException(400, "Template DNA file missing")

    bp = json.loads(dna_path.read_text("utf-8"))
    bp["source"] = {
        "title": row["name"],
        "channel": f"Template: {row['name']}",
        "duration_s": 0,
    }
    (sdir / "blueprint.json").write_text(json.dumps(bp, indent=2, ensure_ascii=False), "utf-8")

    # Create session (starts at reverse_done to skip reverse, lands on Ideas)
    now = dt.datetime.now(dt.UTC).isoformat()
    session = {
        "id": sid,
        "template_id": req.template_id,
        "template_name": row["name"],
        "url": None,
        "yt_title": req.topic or row["name"],
        "yt_channel": "Template",
        "step": "reverse_done",  # skip reverse step, start at ideas
        "idea": None,
        "voice_id": req.voice_id or cfg.get("elevenlabs.default_voice_id", ""),
        "duration_min": 5,
        "created_at": now,
        "updated_at": now,
    }
    _save(sid, session)

    return {"session_id": sid, "ok": True}
