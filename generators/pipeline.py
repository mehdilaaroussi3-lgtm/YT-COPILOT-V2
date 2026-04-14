"""Thumbnail generation pipeline.

Flow (dead simple):
  1. Resolve the channel (scrape + cache if needed).
  2. Pull its top thumbnails as visual references.
  3. For each requested variant, pick a different reference thumbnail.
  4. Prompt Gemini: "Here is a reference from @channel. Make a new
     thumbnail for the video titled X. Match the reference's style exactly,
     adapt only the subject matter to fit the title."
  5. Emit each variant to the UI as soon as it finishes.

No niche detection. No scene formula. No brand-profile layer. One channel
in, N channel-style thumbnails out.
"""
from __future__ import annotations

import datetime as dt
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

from cli import config as cfg
from compositing.effects import apply_post
from core.concept_planner import plan_concepts
from core.pairing_validator import validate_pairing
from core.style_channel import resolve_style_channel
from core.text_extractor import extract_hook
from generators.gemini_client import GeminiImage, GeminiImageClient


@dataclass
class VariantOutput:
    variant: str
    file_path: str
    prompt: str
    reference_used: str
    score: float | None
    score_issues: list[str]


@dataclass
class PipelineResult:
    title: str
    channel: str
    output_dir: str
    text_hook: str
    pairing_score: int
    pairing_issues: list[str]
    variants: list[VariantOutput]
    references_used: list[str]
    metadata_path: str
    # Kept for backward-compat with callers that still read these:
    niche: str = ""
    mockup_dark: str = ""
    mockup_light: str = ""


def _slugify(text: str, n: int = 40) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    return s[:n] or "untitled"


COPYCAT_PROMPT = """\
Generate a YouTube thumbnail at 1280x720 (16:9).

{image_roles}
{sketch_block}
VIDEO TITLE: "{title}"

DEPICT THIS SPECIFIC SCENE (this is WHAT the image should show):
{concept}

MATCH THE CHANNEL REFERENCE on all of these (how it should look):
- color palette and saturation
- lighting direction, quality, and temperature
- level of realism vs illustration / photography vs graphic
- emotional tone and pacing
- textures, grain, halation, and any recurring treatments
- typography treatment if text is present (font character, placement,
  color, stroke/shadow) — if the channel reference has no on-image text,
  do not invent one

{hook_line}
{brief_block}
Do not regress to a generic dramatic AI-thumbnail look. Render the scene
above in the channel's visual language. Content comes from the scene
description (and the sketch if provided), never from the channel reference.

Output ONE image, 16:9 widescreen, 1280x720.
"""

IMAGE_ROLE_CHANNEL_ONLY = """\
I've attached ONE reference thumbnail from the YouTube channel @{channel}.
This reference IS the STYLE target — use it for HOW the image should look.
DO NOT reuse its subject matter. DO NOT copy its people, places, objects or
on-image text. The reference controls treatment, not content."""

IMAGE_ROLE_SKETCH_PLUS_CHANNEL = """\
I've attached TWO images, in this order:

  IMAGE 1 — LAYOUT SKETCH (from the user, hand-drawn).
  This is a composition blueprint. Honour the spatial intent EXACTLY: where
  the main subject sits, where secondary elements go, what is below/above it,
  where empty space breathes, rough proportions and framing. If the sketch
  shows a pyramid on a horizon, your output must have a pyramid on a
  horizon — NOT a pyramid on a machine, a building, a server, or any other
  channel-specific object. Ground stays ground. Sky stays sky. Do NOT
  replace sketched elements with channel-specific props even if those props
  are on-brand for the channel.
  Ignore the sketch's line style, colors, and any faded/light-grey/erased
  scribbles — those are noise. Only the bold, clearly-drawn composition
  counts. Render the final image as a photograph/illustration (in the
  channel's style), NOT as a drawing.
  A plain-English transcription of the sketch composition is given below
  under "SKETCH COMPOSITION" — treat it as authoritative.

  IMAGE 2 — CHANNEL STYLE REFERENCE from @{channel}.
  This is the STYLE target — use it for HOW the image should look (lighting,
  palette, grain, mood, rendering). DO NOT reuse its subject matter, people,
  places, objects, or on-image text. The channel reference controls
  treatment, not content."""


def _build_prompt(title: str, hook: str, channel: str, concept: str,
                    style_brief: str | None, no_text: bool,
                    has_sketch: bool = False,
                    sketch_description: str = "") -> str:
    hook_line = ""
    if no_text:
        hook_line = "Do NOT render any text, letters, or words in the image.\n"
    elif hook:
        is_multiline = "\n" in hook
        if is_multiline:
            lines = [ln.strip() for ln in hook.split("\n") if ln.strip()]
            layout_note = (
                f" This is {len(lines)}-line text — render the lines stacked "
                f"vertically exactly in this order: "
                + " | ".join(f'"{ln}"' for ln in lines)
                + ". Each line is its own block."
            )
            rendered = "\n".join(lines)
        else:
            layout_note = ""
            rendered = hook
        hook_line = (
            f'Render this EXACT text on the thumbnail (preserve casing and line breaks):\n'
            f'"""\n{rendered}\n"""\n'
            f'Style the text to match the channel\'s typographic DNA visible in the '
            f'reference image — same font character (tall/condensed/rounded), weight, '
            f'placement, color, stroke/shadow treatment.{layout_note}\n'
            f'Do not invent additional text beyond what is quoted above.\n'
        )
    brief_block = f"\nChannel style brief (derived from the channel's thumbnails):\n{style_brief}\n" if style_brief else ""
    image_roles = (
        IMAGE_ROLE_SKETCH_PLUS_CHANNEL if has_sketch else IMAGE_ROLE_CHANNEL_ONLY
    ).format(channel=channel)
    sketch_block = (
        f"\nSKETCH COMPOSITION (authoritative layout — render exactly this):\n{sketch_description}\n"
        if has_sketch and sketch_description else ""
    )
    return COPYCAT_PROMPT.format(
        channel=channel, title=title, concept=concept,
        hook_line=hook_line, brief_block=brief_block,
        image_roles=image_roles, sketch_block=sketch_block,
    )


def run_pipeline(
    title: str,
    channel: str = "",
    *,
    script: str | None = None,       # kept for signature compat, unused
    sketch: Path | None = None,
    reference: Path | None = None,
    no_text: bool = False,
    variants: int = 1,
    do_mockup: bool = False,         # kept for compat, ignored
    do_quality: bool = True,
    on_progress: Callable[[str], None] | None = None,
    on_variant_done: Callable[[dict], None] | None = None,
    should_cancel: Callable[[], bool] | None = None,
    out_root: Path | None = None,
    style_channel_id: str | None = None,
) -> PipelineResult:
    log = on_progress or (lambda _msg: None)
    emit_variant = on_variant_done or (lambda _d: None)
    cancel_check = should_cancel or (lambda: False)

    channel_ref = style_channel_id or channel
    if not channel_ref:
        raise RuntimeError("A channel (ID or @handle) is required.")

    log(f"Scraping thumbnails from {channel_ref}...")
    sc = resolve_style_channel(
        channel_ref,
        handle_or_url=channel_ref if not channel_ref.startswith("UC") else None,
    )
    if not sc or not sc.get("all_reference_paths"):
        raise RuntimeError(
            f"Could not resolve channel '{channel_ref}'. "
            "Check the ID/@handle and make sure the channel has public videos."
        )

    channel_label = sc.get("handle") or sc.get("name") or channel_ref
    all_refs: list[Path] = list(sc.get("all_reference_paths") or sc.get("reference_paths") or [])
    style_brief: str | None = sc.get("style_brief") or None
    text_dna: str = sc.get("text_dna") or ""
    log(f"  {len(all_refs)} thumbnails cached from @{channel_label}")
    if style_brief:
        log(f"  Style brief: {len(style_brief)} chars")
    if text_dna:
        log(f"  Text DNA: {len(text_dna)} chars")

    n_variants = max(1, min(int(variants or 1), 8))
    sketch_description = ""
    if sketch:
        log("Sketch attached — reading its composition with Vision...")
        try:
            from core.sketch_reader import describe_sketch
            sketch_description = describe_sketch(sketch)
        except Exception as e:  # noqa: BLE001
            log(f"  Sketch read failed: {e}")
            sketch_description = ""
        if sketch_description:
            log(f"  Sketch composition: {sketch_description[:200]}")
        else:
            log("  (sketch description empty — falling back to raw bitmap only)")
        log("The sketch will act as the layout blueprint on every variant.")

    # Channel-DNA decides which variants carry text. User's "No text" toggle
    # always wins. Otherwise: text-free channels skip text, heavy-text channels
    # always bake it, middle channels get a MIX across variants.
    from core.channel_text_dna import (
        generate_smart_hook, generate_smart_hooks, get_text_usage, plan_text_slots,
    )
    text_usage = get_text_usage(text_dna)
    text_slots = plan_text_slots(text_usage, n_variants, user_forced_no_text=no_text)
    text_count = sum(1 for s in text_slots if s)
    if no_text:
        log(f"User disabled text — all {n_variants} variant(s) text-free.")
    else:
        log(f"Channel text usage: {text_usage} — {text_count}/{n_variants} variant(s) will carry text.")

    hooks_per_variant: list[str] = [""] * n_variants
    if text_count > 0:
        raw_hooks: list[str] = []
        if text_dna:
            if text_count > 1:
                raw_hooks = generate_smart_hooks(title, text_dna, n=text_count)
            else:
                single = generate_smart_hook(title, text_dna)
                raw_hooks = [single] if single else []
        if not raw_hooks:
            log("  (smart hooks missing — falling back to regex hook)")
            fallback = extract_hook(title)
            raw_hooks = [fallback] * text_count
        # Pad if the model returned fewer than requested
        while len(raw_hooks) < text_count:
            raw_hooks.append(raw_hooks[-1] if raw_hooks else extract_hook(title))
        # Drop hooks into the True slots, in order
        hook_idx = 0
        for i, want_text in enumerate(text_slots):
            if want_text and hook_idx < len(raw_hooks):
                hooks_per_variant[i] = raw_hooks[hook_idx]
                hook_idx += 1

    for i, h_ in enumerate(hooks_per_variant, 1):
        log(f'  Variant [{i}]: ' + (f'"{h_}"' if h_ else "(text-free)"))

    hook = next((h for h in hooks_per_variant if h), "")
    pairing = validate_pairing(title, hook)

    # Output dir
    today = dt.date.today().isoformat()
    out_root = out_root or Path(cfg.get("defaults.output_dir", "output"))
    out_dir = out_root / f"{today}_{_slugify(title)}"
    out_dir.mkdir(parents=True, exist_ok=True)

    client = GeminiImageClient.from_config()

    score_fn = None
    if do_quality:
        from generators.quality_gate import describe, heuristic_score
        score_fn = (describe, heuristic_score)

    log(f"Planning {n_variants} visual concept(s) for the title...")
    concepts = plan_concepts(title, channel_label, style_brief, n=n_variants)
    for i, c in enumerate(concepts[:n_variants], 1):
        log(f"  [{i}] {c[:120]}")

    variant_outputs: list[VariantOutput] = []
    used_refs: list[Path] = []
    prompts_built: list[str] = []

    for i in range(n_variants):
        if cancel_check():
            log("Cancelled.")
            break
        vkey = str(i + 1)

        # Pick the CHANNEL reference for this variant — SPREAD across the
        # collection (not just top-N consecutively) so variants see
        # structurally different references.
        if not all_refs:
            raise RuntimeError("No channel references available.")
        if n_variants == 1 or len(all_refs) == 1:
            channel_ref = all_refs[0]
        else:
            idx = int(i * (len(all_refs) - 1) / (n_variants - 1))
            channel_ref = all_refs[idx]

        # Build the reference image list. Sketch (if present) is IMAGE 1 on
        # EVERY variant as the layout blueprint. Channel ref is IMAGE 2 as
        # the style target. User's extra upload falls back as the style ref
        # only when no channel ref is available (edge case).
        refs_for_variant: list[Path] = []
        if sketch:
            refs_for_variant.append(sketch)
        refs_for_variant.append(channel_ref)
        # Extra user reference, only included if Gemini still has a free slot
        if reference and len(refs_for_variant) < 2:
            refs_for_variant.append(reference)
        used_refs.append(channel_ref)

        concept = concepts[i] if i < len(concepts) else title
        variant_hook = (hooks_per_variant[i] if i < len(hooks_per_variant) else hook) or ""
        # Per-variant text decision: if this slot has no hook, tell Gemini
        # explicitly not to render text. Prevents model from adding its own.
        variant_no_text = no_text or not variant_hook
        prompt_text = _build_prompt(
            title, variant_hook, channel_label, concept, style_brief,
            variant_no_text, has_sketch=bool(sketch),
            sketch_description=sketch_description,
        )
        prompts_built.append(prompt_text)
        log(f"Generating variant {vkey}/{n_variants} (refs: "
            + ", ".join(p.name for p in refs_for_variant) + ")...")
        try:
            img: GeminiImage = client.generate(prompt_text, reference_images=refs_for_variant)
        except Exception as e:  # noqa: BLE001
            log(f"  Variant {vkey} failed: {e}")
            emit_variant({"variant": vkey, "error": str(e)})
            continue

        final_path = out_dir / f"variant_{vkey}.png"
        final_path.write_bytes(img.data)
        apply_post(final_path, final_path, grain=0, vignette=False, grade=None)

        score_val: float | None = None
        issues: list[str] = []
        if score_fn:
            try:
                desc = score_fn[0](final_path)
                score_val, issues = score_fn[1](desc)
            except Exception as e:  # noqa: BLE001
                log(f"  Quality gate skipped: {e}")

        vo = VariantOutput(
            variant=vkey,
            file_path=str(final_path),
            prompt=prompt_text,
            reference_used=str(channel_ref),
            score=score_val,
            score_issues=issues,
        )
        variant_outputs.append(vo)
        emit_variant({
            "variant": vkey,
            "file_path": str(final_path),
            "score": score_val,
            "issues": issues,
        })

    # Defensive coercion — anywhere a Path could leak in, force str.
    def _s(v):
        from pathlib import PurePath
        if isinstance(v, PurePath):
            return str(v)
        if isinstance(v, dict):
            return {k: _s(x) for k, x in v.items()}
        if isinstance(v, (list, tuple)):
            return [_s(x) for x in v]
        return v

    # Persist to history
    try:
        from data.db import db as _db
        _d = _db()
        now = dt.datetime.now(dt.UTC).isoformat()
        for vo in variant_outputs:
            _d["generations"].insert(_s({
                "title": title,
                "channel": channel_ref,
                "niche": channel_label,
                "variant": vo.variant,
                "file_path": vo.file_path,
                "prompt": vo.prompt[:4000],
                "references_used": json.dumps([str(vo.reference_used)]),
                "score": float(vo.score or 0.0),
                "cost_usd": 0.0,
                "created_at": now,
            }), alter=True)
    except Exception as e:  # noqa: BLE001
        log(f"  DB persist skipped: {e}")

    # metadata.json
    meta = _s({
        "title": title,
        "channel": channel_ref,
        "channel_label": channel_label,
        "timestamp": dt.datetime.now(dt.UTC).isoformat(),
        "text_hook": hook,
        "pairing": asdict(pairing),
        "references_used": [str(p) for p in used_refs],
        "style_brief_present": bool(style_brief),
        "variants": [asdict(v) for v in variant_outputs],
    })
    meta_path = out_dir / "metadata.json"
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    (out_dir / "prompts.txt").write_text(
        "\n\n===\n\n".join(f"VARIANT {i+1}\n{p}" for i, p in enumerate(prompts_built)),
        encoding="utf-8",
    )

    log("Done.")
    return PipelineResult(
        title=title,
        channel=channel_ref,
        output_dir=str(out_dir),
        text_hook=hook,
        pairing_score=pairing.score,
        pairing_issues=pairing.issues,
        variants=variant_outputs,
        references_used=[str(p) for p in used_refs],
        metadata_path=str(meta_path),
        niche=channel_label,
    )
