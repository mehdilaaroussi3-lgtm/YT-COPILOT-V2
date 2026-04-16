"""Stage 8: transcript — YouTube captions first, faster-whisper fallback."""
from __future__ import annotations

from pathlib import Path

from cli import config as cfg


def _parse_vtt(vtt: Path) -> list[dict]:
    import webvtt
    segs: list[dict] = []
    for c in webvtt.read(str(vtt)):
        start = _ts_to_s(c.start)
        end = _ts_to_s(c.end)
        text = " ".join(l.strip() for l in c.text.splitlines() if l.strip())
        if text:
            segs.append({"start": start, "end": end, "text": text})
    return _dedupe(segs)


def _ts_to_s(ts: str) -> float:
    parts = ts.replace(",", ".").split(":")
    h, m, s = (["0"] * (3 - len(parts))) + parts
    return int(h) * 3600 + int(m) * 60 + float(s)


def _dedupe(segs: list[dict]) -> list[dict]:
    """YouTube auto-captions often repeat rolling lines. Keep first occurrence."""
    out: list[dict] = []
    seen: set[str] = set()
    for s in segs:
        key = s["text"].lower()
        if key in seen:
            # extend previous end time
            if out:
                out[-1]["end"] = s["end"]
            continue
        seen.add(key)
        out.append(s)
    return out


def _whisper(mp4: Path) -> list[dict]:
    from faster_whisper import WhisperModel
    model_name = cfg.get("reverse.whisper_model") or "base"
    model = WhisperModel(model_name, compute_type="int8")
    segments, _info = model.transcribe(str(mp4), vad_filter=True)
    return [{"start": float(s.start), "end": float(s.end), "text": s.text.strip()}
            for s in segments if s.text.strip()]


def transcribe(mp4: Path, vtt: Path | None, whisper_enabled: bool = True) -> list[dict]:
    if vtt and vtt.exists():
        try:
            segs = _parse_vtt(vtt)
            if segs:
                return segs
        except Exception:  # noqa: BLE001
            pass
    if not whisper_enabled:
        return []
    return _whisper(mp4)


def align_to_scenes(segments: list[dict], scenes: list[dict]) -> list[dict]:
    """Attach scene_idx to each transcript segment by mid-point overlap."""
    out = []
    for seg in segments:
        mid = (seg["start"] + seg["end"]) / 2.0
        scene_idx = None
        for sc in scenes:
            if sc["start"] <= mid < sc["end"]:
                scene_idx = sc["idx"]
                break
        out.append({**seg, "scene_idx": scene_idx})
    return out
