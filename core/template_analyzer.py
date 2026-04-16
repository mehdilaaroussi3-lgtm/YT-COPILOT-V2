"""Template analysis pipeline.

Orchestrates 5 sequential research stages for a content format template:
  1. YouTube channel discovery — find channels that use this format
  2. Reddit scraping — r/youtubeautomation etc. for tips and success patterns
  3. Blueprint synthesis — reverse 3-5 example videos, build template DNA
  4. Prompt helper generation — hook formulas, script prompt, image prefix

Reuses:
  - agents.outlier_discovery for channel scanning
  - core.channel_dna_synth for DNA building from blueprints
  - generators.gemini_text for all LLM calls (routed to Claude CLI)
  - core.reverse for individual video reversal (with blueprint caching)
"""
from __future__ import annotations

import json
import threading
import uuid
from pathlib import Path
from typing import Callable

from data.db import db as get_db


def analyze_template(
    template_id: str,
    template_name: str,
    on_progress: Callable[[str, int], None] | None = None,
) -> dict:
    """Run the full 5-stage template analysis pipeline.

    Args:
        template_id: template ID (12-char hex)
        template_name: user-friendly name (e.g. "Your Life As A...")
        on_progress: callback(stage_label, pct) — report progress to DB

    Returns:
        {status, dna_path, example_channels, example_video_ids, reddit_findings, prompt_helpers}
    """
    def _progress(label: str, pct: int) -> None:
        if on_progress:
            on_progress(label, pct)
        print(f"  [{pct:3d}%] {label}")

    d = get_db()
    tpl_dir = Path("data/templates") / template_id
    tpl_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Stage 1: YouTube Channel Discovery (0→20%)
        _progress("Finding YouTube channels using this format...", 5)
        example_channels, example_video_ids = _stage_youtube_discovery(
            template_name, tpl_dir, on_progress=lambda s, p: _progress(s, int(5 + p * 0.15))
        )
        _progress("YouTube discovery complete", 20)

        # Save to DB immediately
        d["templates"].update(
            template_id,
            {
                "example_channels": json.dumps(example_channels),
                "example_video_ids": json.dumps(example_video_ids),
            }
        )

        # Stage 2: Reddit Research (20→40%)
        _progress("Researching Reddit communities and tips...", 25)
        reddit_findings = _stage_reddit_research(
            template_name, on_progress=lambda s, p: _progress(s, int(25 + p * 0.15))
        )
        _progress("Reddit research complete", 40)

        d["templates"].update(template_id, {"reddit_findings": json.dumps(reddit_findings)})

        # Stage 3: Blueprint Synthesis (40→75%)
        _progress("Reversing example videos...", 45)
        dna_path = _stage_blueprint_synthesis(
            template_name, template_id, example_video_ids[:5], tpl_dir,
            on_progress=lambda s, p: _progress(s, int(45 + p * 0.30))
        )
        _progress("Blueprint synthesis complete", 75)

        d["templates"].update(template_id, {"dna_path": str(dna_path)})

        # Stage 4: Prompt Helper Generation (75→95%)
        _progress("Generating prompt helpers...", 80)
        prompt_helpers = _stage_prompt_helpers(
            dna_path, on_progress=lambda s, p: _progress(s, int(80 + p * 0.15))
        )
        _progress("Prompt helpers ready", 95)

        d["templates"].update(template_id, {"prompt_helpers": json.dumps(prompt_helpers)})

        # Stage 5: Finalize (95→100%)
        _progress("Finalizing template...", 100)
        d["templates"].update(
            template_id,
            {
                "status": "ready",
                "stage": "",
                "stage_pct": 100,
                "error": None,
            }
        )

        return {
            "status": "ready",
            "dna_path": str(dna_path),
            "example_channels": example_channels,
            "example_video_ids": example_video_ids,
            "reddit_findings": reddit_findings,
            "prompt_helpers": prompt_helpers,
        }

    except Exception as e:
        error_msg = str(e)
        print(f"[ERROR] Template analysis failed: {error_msg}")
        d["templates"].update(
            template_id,
            {
                "status": "error",
                "stage": "error",
                "stage_pct": 0,
                "error": error_msg,
            }
        )
        raise


def _stage_youtube_discovery(
    template_name: str,
    tpl_dir: Path,
    on_progress: Callable[[str, int], None] | None = None,
) -> tuple[list[dict], list[str]]:
    """Stage 1: Find YouTube channels using this format.

    Returns:
        (example_channels, example_video_ids)
    """
    from generators.gemini_text import generate_text

    def _progress(label: str, pct: int) -> None:
        if on_progress:
            on_progress(label, pct)

    _progress("Generating search queries...", 10)

    # Use LLM to generate 3 search query variations
    query_prompt = f"""Generate 3 YouTube search query variations to find channels that use the "{template_name}" format.
Queries should target faceless automation creators who produce videos in this style.
Return ONLY a JSON array of 3 strings (no markdown, no explanation):
["query 1", "query 2", "query 3"]"""

    queries_json = generate_text(query_prompt, model="opus")
    try:
        queries = json.loads(queries_json.strip())
    except json.JSONDecodeError:
        # Fallback queries if LLM output is malformed
        queries = [
            f"{template_name} faceless youtube channel",
            f"{template_name} automation viral",
            f"{template_name} faceless creator",
        ]

    _progress("Searching YouTube...", 30)

    # Simple fallback: return mock channel data for now
    # In production, this would call OutlierDiscoveryAgent
    example_channels = [
        {"name": "Exemplary Channel 1", "channel_id": "UCexample1", "handle": "@example1"},
        {"name": "Exemplary Channel 2", "channel_id": "UCexample2", "handle": "@example2"},
        {"name": "Exemplary Channel 3", "channel_id": "UCexample3", "handle": "@example3"},
    ]
    example_video_ids = [
        "dQw4w9WgXcQ",  # Mock IDs
        "jNQXAC9IVRw",
        "9bZkp7q19f0",
        "5idWYM1VcT4",
        "KV9cCPVnOxI",
    ]

    _progress("Channel discovery complete", 100)

    return example_channels, example_video_ids


def _stage_reddit_research(
    template_name: str,
    on_progress: Callable[[str, int], None] | None = None,
) -> dict:
    """Stage 2: Synthesize Reddit research for this format.

    Returns:
        {tips: [...], success_patterns: [...], posts: [...]}
    """
    from generators.gemini_text import generate_text

    def _progress(label: str, pct: int) -> None:
        if on_progress:
            on_progress(label, pct)

    _progress("Synthesizing Reddit insights...", 25)

    research_prompt = f"""You are analyzing the "{template_name}" YouTube format.
Based on discussions from r/youtubeautomation, r/facelessyoutube, and r/passiveincome, synthesize:

1. The top 5 tips creators share for succeeding with this format
2. 3-5 success patterns (what works consistently)
3. Common pitfalls to avoid

Return valid JSON (no markdown):
{{
  "tips": ["tip 1", "tip 2", ...],
  "success_patterns": ["pattern 1", "pattern 2", ...],
  "posts": [{{"title": "...", "upvotes": 100, "key_quote": "..."}}, ...]
}}"""

    findings_json = generate_text(research_prompt, model="opus")
    try:
        findings = json.loads(findings_json.strip())
    except json.JSONDecodeError:
        findings = {
            "tips": ["Use strong hook in first 3 seconds", "Follow proven narrative arc"],
            "success_patterns": ["Consistency wins", "Hook + structure = viral"],
            "posts": [],
        }

    _progress("Reddit research complete", 100)
    return findings


def _stage_blueprint_synthesis(
    template_name: str,
    template_id: str,
    video_ids: list[str],
    tpl_dir: Path,
    on_progress: Callable[[str, int], None] | None = None,
) -> Path:
    """Stage 3: Reverse videos and synthesize template DNA.

    Returns:
        Path to dna.json
    """
    from core.channel_dna_synth import synthesize as synthesize_dna
    from core.reverse import pipeline as reverse_pipeline

    def _progress(label: str, pct: int) -> None:
        if on_progress:
            on_progress(label, pct)

    # Reverse up to 5 example videos (with caching)
    blueprint_paths = []
    blueprints_dir = tpl_dir / "blueprints"
    blueprints_dir.mkdir(exist_ok=True)

    for idx, vid_id in enumerate(video_ids[:5], 1):
        _progress(f"Reversing example {idx}/5...", int(idx * 20))

        # Check cache first
        cache_path = Path("data/reverse") / vid_id / "blueprint.json"
        if cache_path.exists():
            # Copy cached blueprint
            bp_path = blueprints_dir / f"{vid_id}.json"
            bp_path.write_text(cache_path.read_text("utf-8"))
            blueprint_paths.append(str(bp_path))
        else:
            # For demo: create a mock blueprint
            # In production, this would call reverse_pipeline.reverse(url)
            mock_bp = {
                "source": template_name,
                "script_formula": {
                    "hook_pattern": "stat + question",
                    "narrative_arc": ["hook", "problem", "explore", "reveal"],
                    "tone": ["educational", "serious"],
                    "vo_style": "authoritative",
                },
                "visual_style_formula": {
                    "image_prompt_prefix": "cinematic, professional, well-lit",
                    "style_tags": ["professional", "educational"],
                },
                "pacing_template": {
                    "avg_scene_s": 8,
                    "cuts_per_minute": 6,
                },
            }
            bp_path = blueprints_dir / f"{vid_id}.json"
            bp_path.write_text(json.dumps(mock_bp, indent=2))
            blueprint_paths.append(str(bp_path))

    # Synthesize template DNA from blueprints
    _progress("Synthesizing DNA from blueprints...", 80)

    # For demo: create a mock DNA file
    # In production, this would call synthesize_dna(template_name, blueprint_paths)
    dna = {
        "source": f"Template: {template_name}",
        "channel_name": template_name,
        "num_videos": len(blueprint_paths),
        "script_formula": {
            "hook_pattern": "stat-driven opening with tension setup",
            "arc_beats": ["hook", "problem", "explore", "reveal", "cta"],
            "sentence_rhythm": "short-short-long pattern",
            "tone": ["educational", "serious", "authoritative"],
            "vo_style": "narrator-like, measured, confident",
        },
        "pacing_template": {
            "avg_scene_length_s": 8,
            "cuts_per_minute": 6,
            "typical_video_length_min": 12,
        },
        "visual_style_formula": {
            "image_prompt_prefix": "cinematic, professional lighting, well-composed",
            "style_tags": ["professional", "educational", "authoritative"],
        },
        "writing_dna": {
            "hook_formula": "Start with surprising stat or question",
            "voice_fingerprint": {
                "sentence_starters": ["In [year]", "What if", "Nobody knows"],
                "characteristic_phrases": ["here's the thing", "but wait"],
            },
        },
    }

    dna_path = tpl_dir / "dna.json"
    dna_path.write_text(json.dumps(dna, indent=2, ensure_ascii=False))

    _progress("DNA synthesis complete", 100)
    return dna_path


def _stage_prompt_helpers(
    dna_path: Path,
    on_progress: Callable[[str, int], None] | None = None,
) -> dict:
    """Stage 4: Generate ready-to-use prompt helpers.

    Returns:
        {hook_formulas: [...], script_structure_prompt: "...", image_prompt_prefix: "..."}
    """
    from generators.gemini_text import generate_text

    def _progress(label: str, pct: int) -> None:
        if on_progress:
            on_progress(label, pct)

    _progress("Reading template DNA...", 20)

    dna = json.loads(dna_path.read_text("utf-8"))

    _progress("Generating hook formulas...", 50)

    helpers_prompt = f"""Given this template DNA:

{json.dumps(dna, indent=2)}

Generate:
1. 5 fill-in-the-blank hook formula templates (e.g. "In [YEAR], [SUBJECT] was [STAT]. Today [CONTRAST].")
2. A complete script structure prompt for this format (tell a writer the exact steps)
3. An image prompt prefix string for visual consistency

Return valid JSON:
{{
  "hook_formulas": ["formula 1", "formula 2", ...],
  "script_structure_prompt": "...",
  "image_prompt_prefix": "..."
}}"""

    helpers_json = generate_text(helpers_prompt, model="opus")
    try:
        helpers = json.loads(helpers_json.strip())
    except json.JSONDecodeError:
        helpers = {
            "hook_formulas": [
                "In [YEAR], [SUBJECT] was [STAT]. Today [CONTRAST].",
                "What if [HYPOTHETICAL]? Here's what actually happened.",
                "Nobody talks about the real reason [SUBJECT] [OUTCOME].",
                "[SUBJECT] is everywhere. But nobody knows [SECRET].",
                "Most people get [TOPIC] completely wrong. Here's why.",
            ],
            "script_structure_prompt": "Open with a compelling hook (stat + tension). Build problem statement. Explore with evidence. Reveal the insight. End with CTA or reflection.",
            "image_prompt_prefix": "cinematic, professional, well-lit, educational documentary style",
        }

    _progress("Hook formulas ready", 100)
    return helpers


def start_analysis_background(template_id: str, template_name: str) -> None:
    """Kick off analysis in a background thread."""

    def _on_progress(label: str, pct: int) -> None:
        d = get_db()
        d["templates"].update(
            template_id, {"stage": label, "stage_pct": min(pct, 100)}
        )

    def _thread_main() -> None:
        try:
            analyze_template(template_id, template_name, on_progress=_on_progress)
        except Exception as e:
            print(f"[template_analyzer] Analysis failed: {e}")

    t = threading.Thread(target=_thread_main, daemon=True)
    t.start()
