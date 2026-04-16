"""Stage 11: assemble the final blueprint.json.

Uses the Claude text router for:
  (a) per-scene generation prompts (image_prompt + motion_prompt) grounded
      in the scene's vision description and classified production_type
  (b) the 'recommendation' rollup that tells the user how to reproduce the
      video's formula
"""
from __future__ import annotations

import json
import re
import statistics as stats

from generators.gemini_text import generate_text


def _strip_fence(s: str) -> str:
    s = s.strip()
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z]*\n?", "", s)
        s = re.sub(r"\n?```$", "", s)
    return s.strip()


def _pacing(scenes: list[dict], duration_s: float) -> dict:
    if not scenes or duration_s <= 0:
        return {}
    lengths = sorted(sc["duration"] for sc in scenes)
    n = len(lengths)
    # Buckets: hook (0-15s), midsection (15s..last 20%), payoff (last 20%)
    payoff_start = max(duration_s * 0.8, duration_s - 60)
    hook = [sc for sc in scenes if sc["start"] < 15]
    mid = [sc for sc in scenes if 15 <= sc["start"] < payoff_start]
    pay = [sc for sc in scenes if sc["start"] >= payoff_start]

    def cpm(bucket: list[dict], span: float) -> float:
        if span <= 0:
            return 0.0
        return round(len(bucket) * 60.0 / span, 1)

    def percentile(sorted_data: list[float], p: float) -> float:
        if not sorted_data:
            return 0.0
        idx = (p / 100.0) * (len(sorted_data) - 1)
        lo, hi = int(idx), min(int(idx) + 1, len(sorted_data) - 1)
        return round(sorted_data[lo] + (sorted_data[hi] - sorted_data[lo]) * (idx - lo), 2)

    return {
        "hook_window_s": [0, 15],
        "cuts_per_minute": {
            "hook": cpm(hook, min(15.0, duration_s)),
            "midsection": cpm(mid, max(1.0, payoff_start - 15)),
            "payoff": cpm(pay, max(1.0, duration_s - payoff_start)),
        },
        "avg_scene_length_s": round(stats.mean(lengths), 2),
        "stdev_scene_length_s": round(stats.pstdev(lengths), 2) if n > 1 else 0.0,
        "scene_length_percentiles": {
            "p10": percentile(lengths, 10),
            "p50": percentile(lengths, 50),
            "p90": percentile(lengths, 90),
        },
        "scene_count": n,
    }


def _scene_context(sc: dict) -> dict:
    """Compact dict sent to LLM for each scene's prompt generation."""
    return {
        "idx": sc["idx"],
        "duration_s": round(sc["duration"], 2),
        "production_type": sc.get("production_type"),
        "rendering_pipeline": sc.get("rendering_pipeline"),
        "art_direction": sc.get("art_direction", ""),
        "shot_type": sc.get("shot_type"),
        "motion_type": sc.get("motion_type"),
        "description": sc.get("description", ""),
        "on_screen_text": sc.get("on_screen_text", ""),
        "dominant_colors": sc.get("dominant_colors", []),
        "vo": sc.get("vo_segment", ""),
    }


SCENE_PROMPTS_INSTRUCTION = """\
You are generating REPRODUCTION prompts for each scene of a video we're
reverse-engineering. For each scene I give you: its metadata (including
rendering_pipeline and art_direction extracted by vision), the VO line
spoken over it, and the channel's visual style formula.

Your job is to produce prompts that faithfully reproduce the PRODUCTION
METHOD of each scene — not just the subject matter.

  - image_prompt: a Gemini/Midjourney-ready prompt. MUST start with the
    art_direction of the scene (the rendering style), then describe the
    specific visual content matching the VO. Use rendering_pipeline to
    choose the correct approach:
      • ai_generated_image / ai_image_static / ai_image_animated →
        photorealistic AI image prompt with cinematic lighting, ultra-detailed
      • real_camera / live_action / stock_footage →
        documentary/cinematic photography prompt
      • vector_animation / motion_graphic →
        clean vector illustration, flat design, bold colors
      • 3d_render → CGI/3D render prompt with specific lighting rig
      • hand_drawn → illustration medium (watercolor/sketch/oil) prompt
      • screen_capture → no image needed, note "screen recording"
      • composite → photorealistic base + VFX overlay description

  - motion_prompt: for image-to-video (Runway/Kling). Match the original:
      • ken_burns / ai_image_static → camera moves only (slow dolly in/out,
        gentle pan)
      • ai_image_animated / ai_animated → camera move + internal motion
      • talking_head / screen_recording → "n/a" or minimal
      • stock_footage / live_action → describe camera energy

  - camera_move: dolly_in|dolly_out|pan_left|pan_right|tilt_up|tilt_down|
    static|handheld|orbit
  - audio_cue: short note on music/sfx for this beat, or null

Return ONLY JSON: a single list of objects, same order as input, one per
scene, with keys: idx, image_prompt, motion_prompt, camera_move, audio_cue.

Scenes:
{scenes_json}
"""


def _gen_scene_prompts(scenes_full: list[dict]) -> list[dict]:
    # Batch in chunks to keep prompts reasonable
    results: list[dict] = []
    chunk_size = 20
    for i in range(0, len(scenes_full), chunk_size):
        chunk = scenes_full[i:i + chunk_size]
        ctx = [_scene_context(sc) for sc in chunk]
        prompt = SCENE_PROMPTS_INSTRUCTION.format(scenes_json=json.dumps(ctx, indent=2))
        try:
            raw = generate_text(prompt, temperature=0.4)
            raw = _strip_fence(raw)
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                results.extend(parsed)
            else:
                results.extend(parsed.get("scenes", []) if isinstance(parsed, dict) else [])
        except Exception:  # noqa: BLE001
            # Fallback stubs so the blueprint still builds
            for sc in chunk:
                results.append({
                    "idx": sc["idx"],
                    "image_prompt": sc.get("description", ""),
                    "motion_prompt": "",
                    "camera_move": "static",
                    "audio_cue": None,
                })
    # Index results by idx and align back to scenes
    by_idx = {r.get("idx"): r for r in results if isinstance(r, dict)}
    aligned = []
    for sc in scenes_full:
        r = by_idx.get(sc["idx"], {})
        aligned.append({
            "idx": sc["idx"],
            "start": round(sc["start"], 2),
            "end": round(sc["end"], 2),
            "duration_s": round(sc["duration"], 2),
            "production_type": sc.get("production_type"),
            "shot_type": sc.get("shot_type"),
            "image_prompt": r.get("image_prompt", sc.get("description", "")),
            "motion_prompt": r.get("motion_prompt", ""),
            "camera_move": r.get("camera_move", "static"),
            "vo_segment": sc.get("vo_segment", ""),
            "on_screen_text": sc.get("on_screen_text") or None,
            "audio_cue": r.get("audio_cue"),
        })
    return aligned


VISUAL_STYLE_PROMPT = """\
You are extracting the VISUAL AESTHETIC FORMULA of a YouTube channel from its
scene data. Your output will be used to style image-generation prompts for a
completely different topic — so you must strip every topic-specific reference.

CRITICAL RULE — YOU ARE EXTRACTING PRODUCTION METHOD AND AESTHETIC TREATMENT ONLY:
  ✓ Extract: rendering pipeline, lighting style, color grade, texture quality,
    camera treatment, motion style, shot composition, color palette
  ✗ DO NOT extract: what subjects appear in frames, what events are depicted,
    locations, characters, objects, storylines, brand content
  ✗ DO NOT write things like "minimalist icon style" because that describes
    subject matter (icons). Write "flat vector illustration with bold outlines"
    because that describes the rendering method.

Scene data (rendering_pipeline, art_direction, production_type, dominant_colors,
shot_type, motion_type — topic-contaminated description fields are EXCLUDED):
{scenes_json}

Measured color palette (exact hex codes extracted from actual frames):
{hex_palette}

Dominant rendering pipeline across scenes: {dominant_pipeline}

Return ONLY valid JSON:
{{
  "production_method": "one sentence on HOW scenes are made — the rendering pipeline and technique (e.g. 'slow Ken Burns over AI-generated photorealistic stills with cinematic Rembrandt lighting' or 'flat 2D vector motion graphics with bold outlines and solid fill colors')",
  "rendering_pipeline": "the dominant pipeline: ai_generated_image|real_camera|vector_animation|3d_render|hand_drawn|screen_capture|composite",
  "dominant_colors": "palette description embedding the exact hex codes (e.g. 'deep navy #0a0e1a, slate grey #4a5568, warm amber #c8960c')",
  "lighting_style": "lighting approach — only if applicable to the pipeline (e.g. 'dramatic directional Rembrandt, high contrast, moody shadows' for real/AI camera; 'n/a — flat vector' for motion graphics)",
  "shot_composition": "typical framing patterns (e.g. 'centered medium shots, occasional extreme close-ups')",
  "motion_style": "camera/animation motion pattern (e.g. 'slow dolly-in on stills' or 'kinetic 2D transitions with text pop')",
  "visual_mood": "3–5 word aesthetic summary — based on color and rendering, not topic (e.g. 'dark cinematic atmospheric serious' or 'bold energetic flat colorful')",
  "style_tags": ["tag1", "tag2", "tag3", "tag4"],
  "hex_palette": {hex_palette_json},
  "image_prompt_prefix": "A ready-to-use style prefix for Gemini image generation. Must describe the RENDERING METHOD and AESTHETIC only — zero subject matter, zero topic words. Embed exact hex codes. Examples by pipeline: [ai_generated_image] 'Cinematic photorealistic AI still, dramatic Rembrandt lighting, shallow depth of field, color palette #0a0e1a #4a5568 #c8960c, ultra-detailed, 16:9 frame, no text overlays'; [vector_animation] 'Flat 2D vector illustration, bold black outlines, solid fill colors #RRGGBB #RRGGBB, minimal shading, clean geometric shapes, no photorealism'. Write the ACTUAL prefix for THIS channel.",
  "negative_prompt": "comma-separated list of what to NEVER include visually — derived from the channel's aesthetic",
  "avoid": ["visual elements that would look wrong for this channel's aesthetic"]
}}
"""


def _extract_visual_style(scenes_full: list[dict]) -> dict:
    """Derive a topic-stripped visual style formula from sampled scene vision data."""
    from collections import Counter
    # Compact representation — rendering pipeline + aesthetic only, NO description/VO
    scene_data = []
    all_hex: list[str] = []
    pipeline_counts: Counter = Counter()
    for sc in scenes_full:
        entry: dict = {
            "production_type": sc.get("production_type"),
            "rendering_pipeline": sc.get("rendering_pipeline"),
            "art_direction": sc.get("art_direction", ""),
            "dominant_colors": sc.get("dominant_colors", []),
            "shot_type": sc.get("shot_type"),
            "motion_type": sc.get("motion_type"),
        }
        all_hex.extend(sc.get("dominant_colors", []))
        if sc.get("rendering_pipeline"):
            pipeline_counts[sc["rendering_pipeline"]] += 1
        scene_data.append(entry)

    # Deduplicate + rank hex codes by frequency — top 6 are the true palette
    hex_counts = Counter(h.upper() for h in all_hex if h and h.startswith("#"))
    top_hex = [h for h, _ in hex_counts.most_common(6)]
    hex_palette_str = "  ".join(top_hex) if top_hex else "(no color data)"
    hex_palette_json = json.dumps(top_hex)
    dominant_pipeline = pipeline_counts.most_common(1)[0][0] if pipeline_counts else "unknown"

    prompt = VISUAL_STYLE_PROMPT.format(
        scenes_json=json.dumps(scene_data, indent=2),
        hex_palette=hex_palette_str,
        hex_palette_json=hex_palette_json,
        dominant_pipeline=dominant_pipeline,
    )
    try:
        raw = generate_text(prompt, temperature=0.2)
        return json.loads(_strip_fence(raw))
    except Exception:  # noqa: BLE001
        # Fallback: derive mechanically from scene stats
        prod_counts: dict[str, int] = {}
        all_colors: list[str] = []
        all_tags: list[str] = []
        for sc in scenes_full:
            pt = sc.get("production_type", "unknown")
            prod_counts[pt] = prod_counts.get(pt, 0) + 1
            all_colors.extend(sc.get("dominant_colors", []))
            all_tags.extend(sc.get("style_tags", []))
        dominant = max(prod_counts, key=prod_counts.get) if prod_counts else "unknown"
        top_tags = list(dict.fromkeys(all_tags))[:5]
        # Pipeline-aware fallback prefix
        if dominant_pipeline in ("ai_generated_image", "ai_image_static", "ai_image_animated"):
            fallback_prefix = "Cinematic photorealistic AI still, dramatic lighting, ultra-detailed, 16:9 frame, no text overlays"
        elif dominant_pipeline == "vector_animation":
            fallback_prefix = "Flat 2D vector illustration, bold outlines, solid fill colors, clean geometric shapes"
        elif dominant_pipeline == "real_camera":
            fallback_prefix = "Cinematic documentary photography, natural lighting, shallow depth of field, 16:9"
        else:
            fallback_prefix = f"{dominant} style, cinematic, high quality"
        return {
            "production_method": f"Primarily {dominant} scenes",
            "rendering_pipeline": dominant_pipeline,
            "dominant_colors": "",
            "lighting_style": "",
            "shot_composition": "",
            "motion_style": "",
            "visual_mood": " ".join(top_tags[:3]),
            "style_tags": top_tags,
            "hex_palette": top_hex,
            "image_prompt_prefix": fallback_prefix,
            "negative_prompt": "",
            "avoid": [],
        }


RECOMMENDATION_PROMPT = """\
You are writing the 'how to reproduce this video' recommendation for a YouTube
creator. Given the production formula, pacing stats, script formula, and
audio formula, output ONLY JSON:

{{
  "when_reproducing": "2-4 sentence strategic summary of how to replicate the style for a new topic",
  "estimated_cost_per_minute": {{"gemini_images": N, "animation_clips": N, "vo": N}},
  "length_scaling_notes": "how the pacing should scale if target length changes",
  "must_keep": ["the 3 non-negotiable structural elements that make this formula work"],
  "swappable": ["elements that can safely be customized per topic"]
}}

Inputs:
{inputs}
"""


def _recommendation(formula: dict, pacing: dict, script: dict, audio: dict) -> dict:
    inputs = json.dumps({
        "production_formula": formula, "pacing": pacing,
        "script": script, "audio": audio,
    }, indent=2)
    try:
        raw = generate_text(RECOMMENDATION_PROMPT.format(inputs=inputs), temperature=0.3)
        return json.loads(_strip_fence(raw))
    except Exception:  # noqa: BLE001
        return {
            "when_reproducing": (
                f"Use {formula.get('primary')} formula with ~{pacing.get('avg_scene_length_s')}s "
                f"average scene length."
            ),
            "estimated_cost_per_minute": {},
            "length_scaling_notes": "",
            "must_keep": [],
            "swappable": [],
        }


def build(*, video_id: str, metadata: dict, formula: dict,
          scenes_full: list[dict], duration_s: float, transcript_aligned: list[dict],
          script_formula: dict, audio: dict) -> dict:
    # attach VO to each scene from aligned transcript
    by_scene: dict[int, list[str]] = {}
    for t in transcript_aligned:
        if t.get("scene_idx"):
            by_scene.setdefault(t["scene_idx"], []).append(t["text"])
    for sc in scenes_full:
        sc["vo_segment"] = " ".join(by_scene.get(sc["idx"], [])).strip()

    pacing = _pacing(scenes_full, duration_s)
    pacing["cuts_on_beat"] = bool(audio.get("beat_aligned_cuts_pct", 0) >= 40)

    scene_prompts = _gen_scene_prompts(scenes_full)
    visual_style = _extract_visual_style(scenes_full)
    recommendation = _recommendation(formula, pacing, script_formula, audio)

    # Build scene_composition from actual scene data (used by script_gen)
    from collections import Counter as _Counter
    pt_counts = _Counter(sc.get("production_type", "unknown") for sc in scenes_full)
    cm_counts = _Counter(sc.get("motion_type") or "static" for sc in scenes_full)
    scene_composition = {
        "production_type_distribution": dict(pt_counts.most_common()),
        "camera_move_distribution": dict(cm_counts.most_common()),
        "avg_scene_length_s": pacing.get("avg_scene_length_s"),
        "dominant_production_type": pt_counts.most_common(1)[0][0] if pt_counts else "unknown",
    }

    return {
        "video_id": video_id,
        "source": {
            "url": metadata.get("url"),
            "title": metadata.get("title"),
            "channel": metadata.get("channel"),
            "duration_s": duration_s,
        },
        "production_formula": formula,
        "pacing_template": pacing,
        "scene_composition": scene_composition,
        "script_formula": script_formula,
        "audio_formula": {
            "tempo_bpm": audio.get("tempo_bpm", 0.0),
            "music_bed_coverage_pct": audio.get("music_bed_coverage_pct", 0.0),
            "beat_aligned_cuts_pct": audio.get("beat_aligned_cuts_pct", 0.0),
            "music_mood": audio.get("music_mood", ""),
        },
        "visual_style_formula": visual_style,
        "scene_prompts": scene_prompts,
        "recommendation": recommendation,
    }
