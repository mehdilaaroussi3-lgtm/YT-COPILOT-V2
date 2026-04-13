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

I've attached ONE reference thumbnail from the YouTube channel @{channel}.
This reference IS the STYLE target — use it for how the image should look.
DO NOT reuse its subject matter. DO NOT copy its people, places, objects
or on-image text. The reference controls treatment, not content.

VIDEO TITLE: "{title}"

DEPICT THIS SPECIFIC SCENE (this is WHAT the image should show):
{concept}

MATCH THE REFERENCE on all of these (how it should look):
- color palette and saturation
- lighting direction, quality, and temperature
- level of realism vs illustration / photography vs graphic
- emotional tone and pacing
- textures, grain, halation, and any recurring treatments
- typography treatment if text is present (font character, placement,
  color, stroke/shadow) — if the reference has no on-image text, do not
  invent one

{hook_line}
{brief_block}
Do not regress to a generic dramatic AI-thumbnail look. Render the scene
above in the reference's visual language. The subject, setting, and action
come entirely from the scene description — not from the reference.

Output ONE image, 16:9 widescreen, 1280x720.
"""


def _build_prompt(title: str, hook: str, channel: str, concept: str,
                    style_brief: str | None, no_text: bool) -> str:
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
    return COPYCAT_PROMPT.format(
        channel=channel, title=title, concept=concept,
        hook_line=hook_line, brief_block=brief_block,
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

    # User's own sketch/reference takes priority — inserted as slot 1.
    user_refs = [p for p in [sketch, reference] if p]

    n_variants = max(1, min(int(variants or 1), 8))

    # Smart hook generation — channel-native text, one DIFFERENT hook per variant.
    hook = ""
    hooks_per_variant: list[str] = []
    if not no_text:
        if text_dna:
            log(f"Generating {n_variants} channel-native hook(s) from text DNA...")
            from core.channel_text_dna import generate_smart_hook, generate_smart_hooks
            if n_variants > 1:
                hooks_per_variant = generate_smart_hooks(title, text_dna, n=n_variants)
            else:
                single = generate_smart_hook(title, text_dna)
                hooks_per_variant = [single] if single else []
        if not hooks_per_variant:
            log("  (smart hooks missing — falling back to regex hook for all variants)")
            fallback = extract_hook(title)
            hooks_per_variant = [fallback] * n_variants
        # Pad with the last hook if the model returned fewer than requested
        while len(hooks_per_variant) < n_variants:
            hooks_per_variant.append(hooks_per_variant[-1] if hooks_per_variant else extract_hook(title))
        hook = hooks_per_variant[0]
        for i, h_ in enumerate(hooks_per_variant, 1):
            log(f'  Hook [{i}]: "{h_}"')
    else:
        hooks_per_variant = [""] * n_variants
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

        # Pick the reference for this variant. User's own refs fill slot 1+2;
        # channel refs are SPREAD across the collection (not just top-N
        # consecutively) so variants see structurally different references.
        if i < len(user_refs):
            ref = user_refs[i]
        elif all_refs:
            channel_slot = i - len(user_refs)
            channel_slots = max(1, n_variants - len(user_refs))
            if channel_slots == 1 or len(all_refs) == 1:
                ref = all_refs[0]
            else:
                idx = int(channel_slot * (len(all_refs) - 1) / (channel_slots - 1))
                ref = all_refs[idx]
        else:
            raise RuntimeError("No references available.")
        used_refs.append(ref)

        concept = concepts[i] if i < len(concepts) else title
        variant_hook = (hooks_per_variant[i] if i < len(hooks_per_variant) else hook) or ""
        prompt_text = _build_prompt(title, variant_hook, channel_label, concept, style_brief, no_text)
        prompts_built.append(prompt_text)
        log(f"Generating variant {vkey}/{n_variants} (reference: {ref.name})...")
        try:
            img: GeminiImage = client.generate(prompt_text, reference_images=[ref])
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
            reference_used=str(ref),
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

    # Persist to history
    try:
        from data.db import db as _db
        _d = _db()
        now = dt.datetime.now(dt.UTC).isoformat()
        for vo in variant_outputs:
            _d["generations"].insert({
                "title": title,
                "channel": channel_ref,
                "niche": channel_label,
                "variant": vo.variant,
                "file_path": vo.file_path,
                "prompt": vo.prompt[:4000],
                "references_used": json.dumps([vo.reference_used]),
                "score": vo.score or 0.0,
                "cost_usd": 0.0,
                "created_at": now,
            }, alter=True)
    except Exception as e:  # noqa: BLE001
        log(f"  DB persist skipped: {e}")

    # metadata.json
    meta = {
        "title": title,
        "channel": channel_ref,
        "channel_label": channel_label,
        "timestamp": dt.datetime.now(dt.UTC).isoformat(),
        "text_hook": hook,
        "pairing": asdict(pairing),
        "references_used": [str(p) for p in used_refs],
        "style_brief_present": bool(style_brief),
        "variants": [asdict(v) for v in variant_outputs],
    }
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
