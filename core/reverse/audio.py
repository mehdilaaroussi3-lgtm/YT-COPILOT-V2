"""Stage 9: audio analysis — beat map, music/speech segmentation,
loudness, cuts-on-beat correlation."""
from __future__ import annotations

from pathlib import Path

import numpy as np


def analyze(mp4: Path, scenes: list[dict]) -> dict:
    """Return audio formula stats for the video."""
    try:
        import librosa
    except Exception:  # noqa: BLE001
        return {"available": False}

    try:
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            y, sr = librosa.load(str(mp4), sr=22050, mono=True, res_type="kaiser_fast")
        y = np.asarray(y, dtype=np.float32)
    except Exception:  # noqa: BLE001
        return {"available": False}

    duration = float(len(y) / sr) if sr else 0.0
    if duration < 1.0:
        return {"available": False}

    # Tempo + beat times
    try:
        tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
        beat_times = librosa.frames_to_time(beats, sr=sr).tolist()
    except Exception:  # noqa: BLE001
        tempo, beat_times = 0.0, []

    # Loudness curve (RMS in 0.5s windows)
    hop = int(sr * 0.5)
    rms = librosa.feature.rms(y=y, frame_length=hop, hop_length=hop)[0]
    loudness = [round(float(v), 4) for v in rms.tolist()]

    # Speech vs music heuristic: spectral flatness (music has lower flatness
    # in tonal sections; speech has more variable flatness). Threshold picked
    # empirically — good enough for a formula hint.
    flat = librosa.feature.spectral_flatness(y=y, hop_length=hop)[0]
    music_mask = (flat < 0.25).astype(int)
    music_coverage = float(music_mask.mean()) if len(music_mask) else 0.0

    # Cuts-on-beat: fraction of scene cuts within 0.2s of a beat time
    cut_times = [sc["start"] for sc in scenes[1:]]
    beat_arr = np.array(beat_times) if beat_times else np.array([])
    on_beat = 0
    for t in cut_times:
        if beat_arr.size and np.min(np.abs(beat_arr - t)) < 0.2:
            on_beat += 1
    beat_aligned_pct = round(100.0 * on_beat / len(cut_times), 1) if cut_times else 0.0

    # Derive a music mood label from tempo + energy characteristics
    bpm = round(float(tempo), 1) if tempo else 0.0
    avg_loudness = float(np.mean(rms)) if len(rms) else 0.0
    if bpm == 0.0 or music_coverage < 0.2:
        music_mood = "ambient/minimal"
    elif bpm < 70:
        music_mood = "dark/cinematic/slow" if avg_loudness > 0.05 else "calm/ambient"
    elif bpm < 100:
        music_mood = "dramatic/orchestral" if avg_loudness > 0.07 else "melancholic/calm"
    elif bpm < 130:
        music_mood = "upbeat/motivational"
    else:
        music_mood = "high-energy/intense"

    return {
        "available": True,
        "duration_s": duration,
        "tempo_bpm": bpm,
        "beat_count": len(beat_times),
        "music_bed_coverage_pct": round(music_coverage * 100.0, 1),
        "beat_aligned_cuts_pct": beat_aligned_pct,
        "music_mood": music_mood,
        "loudness_curve": loudness[:2000],
    }
