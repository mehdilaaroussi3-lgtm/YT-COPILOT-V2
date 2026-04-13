"""Prompt engine — assembles 1of10-style prompts (masterplan §26.6).

Format:
  {title} ({subject_placement}, {expression}, {text_instruction}, {subject_details},
  background is {scene}, {left} to the left, {right} to the right, {lighting},
  {atmosphere}, {brightest_point} is the brightest point,
  high contrast, {saturation_level} saturation)
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.data_rules import rules_summary_for_prompt
from core.scene_generator import SceneConcept


@dataclass
class BuiltPrompt:
    text: str
    references: list[Path]
    variant: str           # "A" | "B" | "C"

    def __repr__(self) -> str:
        return f"BuiltPrompt(variant={self.variant}, refs={len(self.references)}, len={len(self.text)})"


def variant_text_instruction(variant: str, hook: str, profile: dict[str, Any]) -> str:
    primary = profile.get("brand", {}).get("primary_color", "#FFFFFF")
    if variant == "A":
        return (
            f'render bold uppercase text reading "{hook}" in the upper third, '
            f'white with a strong dark stroke, no more than {len(hook.split())} words'
        )
    if variant == "B":
        return (
            "leave the upper third clear and high-contrast for text overlay added later, "
            "do NOT render any text, letters, or words inside the image"
        )
    if variant == "C":
        return (
            "include a clear high-contrast band in the upper third (semi-transparent dark "
            "block) suitable for text overlay; do NOT render any text inside the image"
        )
    return ""


def build_1of10_prompt(
    title: str,
    scene: SceneConcept,
    profile: dict[str, Any],
    variant: str,
    hook: str,
    style_brief: str | None,
    reference_images: list[Path] | None,
    no_text: bool = False,
) -> BuiltPrompt:
    """Channel-copycat prompt: references + brief drive the style, title drives the subject.

    No rigid '1of10 formula', no synthesized brand palette. The provided
    reference thumbnails ARE the style source. Scene is only a loose subject
    suggestion — visual decisions come from the references.
    """
    channel_label = profile.get("handle") or profile.get("name") or "this channel"

    text_instr = ""
    if not no_text and variant == "A":
        text_instr = (
            f'\nTEXT: render the phrase "{hook}" in the image, matching the text '
            "treatment (font character, placement, color, stroke/shadow) seen in "
            "the reference thumbnails. If the references do NOT use on-image text, "
            "leave the image clean — do NOT invent a new text style."
        )
    elif not no_text:
        text_instr = (
            "\nTEXT: leave a clean high-contrast area in the upper third for text "
            "overlay added later. Do NOT render any text, letters, or words."
        )

    refs_line = ""
    if reference_images:
        refs_line = (
            f"I have attached {len(reference_images)} thumbnails from the YouTube "
            f"channel @{channel_label}. These ARE the style target. Your output "
            "must look like it belongs on this channel — same color palette, same "
            "composition logic, same lighting character, same level of realism vs "
            "illustration, same emotional tone, same typography choices.\n\n"
            "Do not produce a generic dramatic thumbnail. Match the references' "
            "restraint or intensity exactly. If the references are clean and "
            "editorial, stay clean and editorial. If they are gritty and cinematic, "
            "be gritty and cinematic. If they lean photographic, lean photographic. "
            "If they lean illustrated, lean illustrated.\n\n"
        )

    brief_line = ""
    if style_brief:
        brief_line = (
            "Per-channel style brief (derived from those same thumbnails):\n"
            f"{style_brief}\n\n"
        )

    scene_hint = (
        f"Primary subject suggestion: {scene.subject}. "
        f"Background: {scene.background}. "
        "Use this only as a starting point — if it conflicts with the channel's "
        "style, prioritize the channel's style.\n"
    )

    full = (
        "Generate a YouTube thumbnail at 1280x720 (16:9).\n\n"
        f"{refs_line}"
        f"{brief_line}"
        f'VIDEO TITLE: "{title}"\n'
        "The thumbnail should complement the title and create a curiosity gap — "
        "do not just illustrate the title literally.\n\n"
        f"{scene_hint}"
        f"{text_instr}\n\n"
        "Output ONE image, 16:9 widescreen, 1280x720."
    )

    return BuiltPrompt(text=full, references=reference_images or [], variant=variant)
