"""Stage 1: generate a structured script.json from topic + blueprint formula.

Text routing hard rule (CLAUDE.md): always use generators.gemini_text.generate_text
which dispatches to the Claude CLI by default.
"""
from __future__ import annotations

import json
import math
import re

from generators.gemini_text import generate_text

PROMPT = """\
You are writing a YouTube video script. You are NOT being creative — you are
replicating a specific creator's voice and applying it to a new topic.
Every sentence you write must sound like it came from this creator.

{deep_dna_block}

═══════════════════════════════════════════════════════════
STRUCTURAL FORMULA (from the reference channel)
═══════════════════════════════════════════════════════════
{formula_block}

═══════════════════════════════════════════════════════════
REAL VO SAMPLES — study STYLE only, topics are irrelevant
═══════════════════════════════════════════════════════════
Hook openings (internalize the exact rhythm and tension setup):
{hook_examples}

Body sentences (internalize word density, punctuation, delivery):
{vo_examples}

Formula notes (how they build narrative tension):
{repro_notes}

═══════════════════════════════════════════════════════════
TITLE FORMULA
═══════════════════════════════════════════════════════════
{title_formula_block}

═══════════════════════════════════════════════════════════
CTA / CLOSER EXAMPLES
═══════════════════════════════════════════════════════════
{cta_examples}

═══════════════════════════════════════════════════════════
YOUR TASK
═══════════════════════════════════════════════════════════
Topic:           {topic}
Target duration: {duration_hint}
Target scenes:   {scene_count} scenes total

Sections to write:
{sections_outline}

HARD RULES — follow every one:
1. HOOK: open with exactly this pattern → {hook_pattern}
2. SENTENCE LENGTH: avg {avg_words} words ±{stdev} — match the samples above.
3. TONE: {tone}
4. VO STYLE: {vo_style}
5. TITLE: follow dominant format '{dominant_title_format}', avg {avg_title_words} words,
   typical openers: {common_title_openers}
6. CLOSER: mirror the CTA style from the examples above exactly.
7. Each scene = 1–3 tight VO sentences. No padding.
8. Every scene needs: image_prompt, camera_move, on_screen_text (null or short string).

═══════════════════════════════════════════════════════════
VISUAL STYLE — apply to EVERY image_prompt
═══════════════════════════════════════════════════════════
This channel's visual aesthetic (topic-stripped):
  Style prefix  : {visual_style_prefix}
  Mood          : {visual_mood}
  Avoid visually: {visual_avoid}

IMAGE PROMPT RULE — follow exactly:
  • Start every image_prompt with the style prefix above
  • Then describe the specific scene subject for "{topic}"
  • Result format: "[style prefix]. [scene-specific subject grounded in {topic}]."
  • NEVER reference anything from the reference channel (its topics, characters, places)
  • The subject matter must be 100% about "{topic}" — the style prefix provides the aesthetic

Return ONLY valid JSON — no prose, no fences:
{{
  "title_suggestion": "title following this channel's formula",
  "sections": [
    {{
      "id": "hook",
      "label": "Hook",
      "scenes": [
        {{
          "idx": 1,
          "vo": "...",
          "image_prompt": "...",
          "camera_move": "dolly_in",
          "on_screen_text": null
        }}
      ]
    }},
    {{
      "id": "section_01",
      "label": "Section 1 — [beat name]",
      "scenes": [...]
    }},
    {{
      "id": "closer",
      "label": "Closer",
      "scenes": [...]
    }}
  ]
}}
"""


def _format_deep_dna(writing_dna: dict) -> str:
    """Format the deep writing DNA into an explicit prompt block.

    This is the primary style guide — placed first in the prompt so it
    dominates over everything else. Each dimension becomes a direct
    instruction, not a vague example to interpret.
    """
    if not writing_dna:
        return ""

    lines: list[str] = [
        "═══════════════════════════════════════════════════════════",
        "CHANNEL VOICE PROFILE  ←  follow every rule below exactly",
        "═══════════════════════════════════════════════════════════",
    ]

    # ── Signature rules — the most critical block ────────────────────
    rules = writing_dna.get("signature_style_rules") or []
    if rules:
        lines.append("\n▸ SIGNATURE STYLE RULES (non-negotiable):")
        for rule in rules:
            lines.append(f"  • {rule}")

    # ── Hook formula ────────────────────────────────────────────────
    hf = writing_dna.get("hook_formula") or {}
    if hf:
        lines.append("\n▸ HOOK FORMULA:")
        if hf.get("opening_move"):
            lines.append(f"  Opening move   : {hf['opening_move']}")
        if hf.get("tension_setup"):
            lines.append(f"  Tension setup  : {hf['tension_setup']}")
        if hf.get("promise_structure"):
            lines.append(f"  Promise        : {hf['promise_structure']}")
        if hf.get("hook_template"):
            lines.append(f"  Template       : {hf['hook_template']}")

    # ── Voice fingerprint ────────────────────────────────────────────
    vf = writing_dna.get("voice_fingerprint") or {}
    if vf:
        lines.append("\n▸ VOICE FINGERPRINT:")
        if vf.get("sentence_starters"):
            lines.append(f"  Sentence starters   : {', '.join(vf['sentence_starters'][:8])}")
        if vf.get("transitional_phrases"):
            lines.append("  Transitional phrases:")
            for p in vf["transitional_phrases"][:6]:
                lines.append(f"    → \"{p}\"")
        if vf.get("emphasis_moves"):
            lines.append(f"  Emphasis moves  : {' | '.join(vf['emphasis_moves'][:4])}")
        if vf.get("characteristic_phrases"):
            lines.append(f"  Characteristic  : {', '.join(repr(p) for p in vf['characteristic_phrases'][:5])}")
        if vf.get("rhythm_tags"):
            lines.append(f"  Rhythm tags     : {', '.join(repr(t) for t in vf['rhythm_tags'][:5])}")

    # ── Sentence architecture ────────────────────────────────────────
    sa = writing_dna.get("sentence_architecture") or {}
    if sa:
        lines.append("\n▸ SENTENCE ARCHITECTURE:")
        if sa.get("dominant_pattern"):
            lines.append(f"  Pattern         : {sa['dominant_pattern']}")
        if sa.get("punctuation_signature"):
            lines.append(f"  Punctuation     : {sa['punctuation_signature']}")
        if sa.get("parallelism"):
            lines.append(f"  Parallelism     : {sa['parallelism']}")
        if sa.get("question_cadence"):
            lines.append(f"  Questions       : {sa['question_cadence']}")

    # ── Tension architecture ─────────────────────────────────────────
    ta = writing_dna.get("tension_architecture") or {}
    if ta:
        lines.append("\n▸ TENSION & BUILD-UP:")
        if ta.get("buildup_method"):
            lines.append(f"  Build method    : {ta['buildup_method']}")
        if ta.get("section_bridge"):
            lines.append(f"  Section bridge  : {ta['section_bridge']}")
        if ta.get("payoff_construction"):
            lines.append(f"  Payoff          : {ta['payoff_construction']}")
        if ta.get("pacing_rhythm"):
            lines.append(f"  Pacing          : {ta['pacing_rhythm']}")

    # ── Information style ────────────────────────────────────────────
    info = writing_dna.get("information_style") or {}
    if info:
        lines.append("\n▸ INFORMATION STYLE:")
        if info.get("presentation_mode"):
            lines.append(f"  Mode            : {info['presentation_mode']}")
        if info.get("perspective"):
            lines.append(f"  Perspective     : {info['perspective']}")
        if info.get("revelation_pattern"):
            lines.append(f"  Revelation      : {info['revelation_pattern']}")
        if info.get("data_use"):
            lines.append(f"  Data use        : {info['data_use']}")

    # ── Emotional arc ────────────────────────────────────────────────
    ea = writing_dna.get("emotional_arc") or {}
    if ea:
        lines.append("\n▸ EMOTIONAL ARC:")
        if ea.get("opening_register"):
            lines.append(f"  Opening         : {ea['opening_register']}")
        if ea.get("mid_video_shift"):
            lines.append(f"  Middle          : {ea['mid_video_shift']}")
        if ea.get("closing_register"):
            lines.append(f"  Closing         : {ea['closing_register']}")
        if ea.get("intensity_profile"):
            lines.append(f"  Intensity       : {ea['intensity_profile']}")

    # ── Vocabulary register ──────────────────────────────────────────
    vr = writing_dna.get("vocabulary_register") or {}
    if vr:
        lines.append("\n▸ VOCABULARY & REGISTER:")
        if vr.get("complexity"):
            lines.append(f"  Complexity      : {vr['complexity']}")
        if vr.get("formality"):
            lines.append(f"  Formality       : {vr['formality']}")
        if vr.get("signature_vocabulary"):
            lines.append(f"  Signature words : {', '.join(repr(w) for w in vr['signature_vocabulary'][:8])}")
        if vr.get("avoided_patterns"):
            lines.append(f"  NEVER do        : {vr['avoided_patterns']}")

    # ── Section template ─────────────────────────────────────────────
    st = writing_dna.get("section_template") or {}
    if st:
        lines.append("\n▸ SECTION TEMPLATE:")
        if st.get("structure"):
            lines.append(f"  Structure       : {' → '.join(st['structure'])}")
        if st.get("hook_length"):
            lines.append(f"  Hook length     : {st['hook_length']}")
        if st.get("beat_length_feel"):
            lines.append(f"  Beat length     : {st['beat_length_feel']}")

    # ── Rhetorical devices ───────────────────────────────────────────
    rd = writing_dna.get("rhetorical_devices") or []
    if rd:
        lines.append(f"\n▸ RHETORICAL DEVICES: {', '.join(rd[:8])}")

    lines.append("")  # trailing newline before next block
    return "\n".join(lines)


def _strip_fence(s: str) -> str:
    s = s.strip()
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z]*\n?", "", s)
        s = re.sub(r"\n?```$", "", s)
    return s.strip()


def _sections_outline(arc_beats: list[dict], total_scenes: int) -> str:
    lines = ["- hook (opening scenes)"]
    mid_beats = arc_beats[1:-1] if len(arc_beats) > 2 else arc_beats
    for i, beat in enumerate(mid_beats, start=1):
        lines.append(f"- section_{i:02d}: {beat.get('beat', '')} — {beat.get('summary', '')[:80]}")
    lines.append("- closer (final scenes)")
    lines.append(f"\nDistribute {total_scenes} scenes across these sections proportionally.")
    return "\n".join(lines)


def _duration_to_scenes(duration_hint: str, avg_scene_s: float) -> int:
    """Convert '10min' / '300s' / '5:30' to scene count estimate."""
    avg_scene_s = max(avg_scene_s, 3.0)
    s = duration_hint.lower().strip()
    total_s = 0.0
    m = re.match(r"(\d+):(\d+)", s)
    if m:
        total_s = int(m.group(1)) * 60 + int(m.group(2))
    elif "min" in s:
        total_s = float(re.sub(r"[^\d.]", "", s)) * 60
    elif "s" in s:
        total_s = float(re.sub(r"[^\d.]", "", s))
    else:
        total_s = float(re.sub(r"[^\d.]", "", s) or "300")
    return max(4, math.ceil(total_s / avg_scene_s))


def generate(blueprint: dict, topic: str, duration_hint: str) -> dict:
    sf = blueprint.get("script_formula") or {}
    pt = blueprint.get("pacing_template") or {}
    arc_beats = sf.get("arc_beats") or [
        {"beat": "setup"}, {"beat": "main"}, {"beat": "payoff"}
    ]
    avg_scene_s = float(pt.get("avg_scene_length_s") or 6.0)
    scene_count = _duration_to_scenes(duration_hint, avg_scene_s)

    sc_comp = blueprint.get("scene_composition") or {}
    formula_block = json.dumps({
        "hook_pattern": sf.get("hook_pattern"),
        "narrative_arc": sf.get("narrative_arc"),
        "sentence_rhythm": sf.get("sentence_rhythm"),
        "tone": sf.get("tone"),
        "vo_style": sf.get("vo_style"),
        "pacing": {
            "avg_scene_s": avg_scene_s,
            "cuts_per_min": pt.get("cuts_per_minute"),
        },
        # Shot vocabulary — structural only, no topic content
        "preferred_camera_moves": list((sc_comp.get("camera_move_distribution") or {}).keys())[:5],
        "dominant_shot_types": list((sc_comp.get("production_type_distribution") or {}).keys())[:3],
    }, indent=2)

    # Pull writing examples from DNA (populated by channel_dna_synth)
    we = blueprint.get("writing_examples") or {}
    hook_examples_list = we.get("hook_text_examples") or []
    vo_examples_list   = we.get("vo_sentence_examples") or []
    repro_notes_list   = we.get("reproducibility_notes") or []

    hook_examples = "\n".join(f'• "{h}"' for h in hook_examples_list) or "(none)"
    vo_examples   = "\n".join(f'• {s}' for s in vo_examples_list[:30]) or "(none)"
    repro_notes   = "\n".join(f'• {n[:300]}' for n in repro_notes_list) or "(none)"

    # Title formula (new — from channel_dna_synth._extract_title_formula)
    tf = blueprint.get("title_formula") or {}
    title_formula_block = json.dumps(tf, indent=2) if tf else "(no title data)"
    dominant_title_format = tf.get("dominant_format", "statement")
    avg_title_words = tf.get("avg_title_words", 8)
    common_title_openers = ", ".join(tf.get("common_opener_words") or []) or "(varied)"

    # CTA examples (from channel_dna_synth._extract_cta_examples)
    cta_list = blueprint.get("call_to_action_examples") or []
    cta_examples = "\n".join(f'• "{c}"' for c in cta_list) or "(none — use a generic subscribe/comment ask)"

    # Deep writing DNA — the new primary style guide
    writing_dna: dict = blueprint.get("writing_dna") or {}
    deep_dna_block = _format_deep_dna(writing_dna)

    # Visual style formula — production-pipeline-aware image prompt routing.
    # We use the rendering_pipeline field (set by the upgraded vision.py) to
    # pick the correct generation approach rather than a simple text scan.
    vsf = blueprint.get("visual_style_formula") or {}
    raw_prefix = vsf.get("image_prompt_prefix") or ""
    rendering_pipeline = (
        vsf.get("rendering_pipeline")
        or (blueprint.get("scene_composition") or {}).get("dominant_production_type")
        or ""
    ).lower()

    # Map rendering pipeline → generation strategy
    _PIPELINE_PRESETS = {
        # Photorealistic AI stills — keep channel style prefix if clean
        "ai_generated_image":  "photo",
        "ai_image_static":     "photo",
        "ai_image_animated":   "photo",
        # Real camera footage → cinematic documentary photography
        "real_camera":         "cinematic",
        "live_action":         "cinematic",
        "stock_footage":       "cinematic",
        # Vector/flat design — honour the style (useful for UI/edu channels)
        "vector_animation":    "vector",
        "motion_graphic":      "vector",
        # 3D render
        "3d_render":           "3d",
        # Hand-drawn / illustration
        "hand_drawn":          "illustration",
        # Screen capture — no image needed per scene, use placeholder
        "screen_capture":      "screen",
        "screen_recording":    "screen",
    }
    strategy = _PIPELINE_PRESETS.get(rendering_pipeline, "photo")

    if strategy == "photo":
        # AI photorealistic — use channel prefix if it looks clean
        _non_photo_markers = (
            "line art", "2d vector", "motion graphic", "diagrammatic",
            "flat color", "flat design", "cartoon", "illustration",
            "hand-drawn", "hand drawn", "infographic", "icon",
        )
        _prefix_is_contaminated = any(m in raw_prefix.lower() for m in _non_photo_markers)
        if raw_prefix and not _prefix_is_contaminated:
            visual_style_prefix = raw_prefix
            visual_mood  = vsf.get("visual_mood") or "cinematic atmospheric"
            visual_avoid = ", ".join(vsf.get("avoid") or []) or "cartoon, illustration, line art, text overlays"
        else:
            visual_style_prefix = (
                "Cinematic photorealistic AI still, ultra-detailed, dramatic lighting, "
                "shallow depth of field, 16:9 frame, no text overlays, no watermarks"
            )
            visual_mood  = "cinematic, tense, documentary"
            visual_avoid = "cartoon, illustration, line art, text overlays, watermark, logo"

    elif strategy == "cinematic":
        visual_style_prefix = raw_prefix if raw_prefix else (
            "Cinematic documentary photography, natural lighting, "
            "shallow depth of field, 16:9 frame, no text overlays"
        )
        visual_mood  = vsf.get("visual_mood") or "documentary cinematic"
        visual_avoid = ", ".join(vsf.get("avoid") or []) or "AI art artifacts, cartoon, text overlays"

    elif strategy == "vector":
        # Vector/motion graphic channels — honour their flat design style
        visual_style_prefix = raw_prefix if raw_prefix else (
            "Flat 2D vector illustration, bold outlines, solid fill colors, "
            "clean geometric shapes, minimal shading, 16:9 frame"
        )
        visual_mood  = vsf.get("visual_mood") or "bold clean flat"
        visual_avoid = ", ".join(vsf.get("avoid") or []) or "photorealism, depth of field, film grain"

    elif strategy == "3d":
        visual_style_prefix = raw_prefix if raw_prefix else (
            "Photorealistic 3D render, cinematic lighting rig, "
            "ultra-detailed textures, 16:9 frame, no text overlays"
        )
        visual_mood  = vsf.get("visual_mood") or "3D cinematic"
        visual_avoid = ", ".join(vsf.get("avoid") or []) or "hand-drawn, flat 2D, cartoon"

    elif strategy == "illustration":
        visual_style_prefix = raw_prefix if raw_prefix else (
            "Digital illustration, painterly style, expressive brushwork, "
            "rich color palette, 16:9 frame"
        )
        visual_mood  = vsf.get("visual_mood") or "illustrated painterly"
        visual_avoid = ", ".join(vsf.get("avoid") or []) or "photorealism, 3D render, flat vector"

    else:  # screen_capture or unknown
        visual_style_prefix = (
            "Cinematic photorealistic still, ultra-detailed, dramatic lighting, "
            "shallow depth of field, 16:9 frame, no text overlays, no watermarks"
        )
        visual_mood  = "cinematic documentary"
        visual_avoid = "cartoon, illustration, line art, text overlays, watermark, logo"

    prompt = PROMPT.format(
        deep_dna_block=deep_dna_block,
        formula_block=formula_block,
        hook_examples=hook_examples,
        vo_examples=vo_examples,
        repro_notes=repro_notes,
        title_formula_block=title_formula_block,
        dominant_title_format=dominant_title_format,
        avg_title_words=avg_title_words,
        common_title_openers=common_title_openers,
        cta_examples=cta_examples,
        visual_style_prefix=visual_style_prefix,
        visual_mood=visual_mood,
        visual_avoid=visual_avoid,
        topic=topic,
        duration_hint=duration_hint,
        scene_count=scene_count,
        sections_outline=_sections_outline(arc_beats, scene_count),
        hook_pattern=sf.get("hook_pattern", "question + stakes"),
        avg_words=sf.get("sentence_rhythm", {}).get("avg_words", 10),
        stdev=sf.get("sentence_rhythm", {}).get("stdev", 4),
        tone=", ".join(sf.get("tone") or ["authoritative"]),
        vo_style=sf.get("vo_style") or "calm narrator",
    )

    raw = generate_text(prompt, temperature=0.4)
    raw = _strip_fence(raw)
    data = json.loads(raw)

    # Re-index scenes globally
    global_idx = 1
    for section in data.get("sections", []):
        for sc in section.get("scenes", []):
            sc["idx"] = global_idx
            global_idx += 1
    return data
