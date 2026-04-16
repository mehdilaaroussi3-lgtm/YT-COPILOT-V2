"""Synthesise a channel DNA from N per-video blueprints produced by URE.

Output: data/channel_dna/<channel_name>/dna.json
Schema mirrors a single blueprint so produce() can consume it unchanged.
"""
from __future__ import annotations
import json, re, statistics
from pathlib import Path

DNA_DIR = Path("data/channel_dna")

# ── Deep writing DNA prompt ────────────────────────────────────────────────
# Sent to Claude after collecting all transcript text.
# Returns an explicit, actionable linguistic profile — not just raw examples.
DEEP_WRITING_DNA_PROMPT = """\
You are a world-class linguistic analyst specializing in YouTube creator voice
replication. Your job: extract every dimension of this creator's writing and
presentation style so precisely that someone could write new scripts that are
INDISTINGUISHABLE from this creator's voice.

Below are transcripts from {n_videos} video(s) by the same creator.

══════════════════════════════════════════
TRANSCRIPTS
══════════════════════════════════════════
{transcript_text}

══════════════════════════════════════════
ANALYSIS TASK
══════════════════════════════════════════

Output STRICT JSON only — no prose, no markdown fences. Every field must be
SPECIFIC and ACTIONABLE. Not "uses short sentences" but "opens each new beat
with a 3–6 word declarative anchor then follows with a 12–20 word explanation."
Not "conversational" but "addresses the viewer as 'you' and uses 'right?' as a
rhythm-closing tag 2–4 times per minute."

{{
  "hook_formula": {{
    "opening_move": "exactly how they start the video — cold-open story? rhetorical question? shocking stat? bold claim? direct address?",
    "tension_setup": "how they create the knowledge gap and stakes in the first 15–30 seconds",
    "promise_structure": "what they explicitly or implicitly promise the viewer",
    "hook_template": "a fill-in-the-blank sentence template capturing their hook structure, e.g. 'In [year], [subject] did something that [consequence]. Here is what nobody told you about it.'"
  }},
  "voice_fingerprint": {{
    "sentence_starters": ["the", "most common", "opening words", "or short phrases", "they use to begin sentences"],
    "transitional_phrases": ["exact phrases they use to move between ideas, e.g. 'Now,', 'But here is the thing:', 'And this is where it gets interesting:'" ],
    "emphasis_moves": ["how they stress a critical point — repetition? sentence fragment? direct call-out? e.g. 'Let me say that again.'"],
    "characteristic_phrases": ["phrases that recur across videos and feel distinctly theirs"],
    "rhythm_tags": ["short verbal tags they use to control pacing — 'right?', 'think about that.', 'seriously.', etc."]
  }},
  "sentence_architecture": {{
    "dominant_pattern": "describe the EXACT sentence rhythm — e.g. 'short 4-word anchor. then a 15-word elaboration. then a one-word or two-word punchline on its own line.'",
    "avg_words_per_sentence": 0,
    "punctuation_signature": "specific use of em-dashes, ellipses, colons, sentence fragments — be exact",
    "parallelism": "do they repeat grammatical structures for effect? give a concrete example from the text",
    "question_cadence": "how and when they deploy rhetorical questions — opener only? end of every beat? scattered?"
  }},
  "tension_architecture": {{
    "buildup_method": "how they escalate — sequential reveals? contrast pairs? deepening stakes? chronological? mystery-first then reveal?",
    "section_bridge": "the exact technique they use to connect one beat to the next — cliffhanger statement? callback? a question? a teaser line?",
    "payoff_construction": "how they deliver the resolution, revelation, or punchline — sudden? built over multiple sentences? with a callback?",
    "pacing_rhythm": "fast info-dense cut-style | slow-burn storytelling | mixed | question-then-answer cadence | list-driven"
  }},
  "information_style": {{
    "presentation_mode": "storytelling | chronological | case-study-per-beat | contrast-pairs | list-of-examples | essay-argument | hybrid",
    "perspective": "first-person narrator ('I was there') | direct 'you' address | third-person observer | god-view narrator | mixed",
    "analogy_style": "do they use analogies? what KIND — everyday objects? pop culture? historical? abstract? give an example if seen",
    "data_use": "how they handle numbers and facts — raw stats dropped with no framing? heavily contextualized? comparative ('that is 10x more than…')? avoided entirely?",
    "revelation_pattern": "when key information is revealed — teased early then detailed later? saved for the end? distributed evenly? buried in the middle?"
  }},
  "emotional_arc": {{
    "opening_register": "the EXACT emotional register of their opening — curious? urgent? conspiratorial? matter-of-fact? alarmed?",
    "mid_video_shift": "how the emotional tone changes through the middle — does it escalate? stay flat? cycle? build dread?",
    "closing_register": "how they end emotionally — satisfied resolution? haunting question? call-to-urgency? warm sign-off?",
    "intensity_profile": "flat | slowly escalating | front-loaded shock then calm | roller-coaster peaks | slow-burn building to single climax"
  }},
  "vocabulary_register": {{
    "complexity": "simple/everyday | conversational-educated | educated-but-accessible | domain-technical",
    "formality": "casual | semi-formal | formal",
    "signature_vocabulary": ["specific words or multi-word phrases this creator favors that feel distinctly theirs"],
    "avoided_patterns": "what this creator NEVER does — passive voice? hedging language? academic jargon? profanity? over-enthusiasm?"
  }},
  "section_template": {{
    "structure": ["hook", "context", "beat_1", "beat_2", "escalation", "payoff", "cta"],
    "typical_beat_count": 3,
    "hook_length": "very short < 20s | short 20–40s | medium 40–75s | long 75s+",
    "beat_length_feel": "each main beat feels like roughly how long? punchy 30s? substantial 90s? variable?"
  }},
  "rhetorical_devices": [
    "list every distinct device observed: 'rule of three', 'false start / correction', 'callback to hook', 'direct address', 'contrast pair (X, not Y)', 'rhetorical question then immediate answer', 'deliberate understatement', etc."
  ],
  "signature_style_rules": [
    "RULE 1: [the single most important, most specific thing about this voice — make it a directive for a writer]",
    "RULE 2: [second most important — equally specific]",
    "RULE 3: ...",
    "RULE 4: ...",
    "RULE 5: ...",
    "RULE 6: ...",
    "RULE 7: ...",
    "RULE 8: [only if genuinely distinct from the above]"
  ]
}}
"""

def synthesize(channel_name: str, blueprint_paths: list[Path], transcript_paths: list[Path] | None = None) -> Path:
    """Merge N blueprints → consensus dna.json. Returns path to dna.json."""
    blueprints = [json.loads(p.read_text(encoding="utf-8")) for p in blueprint_paths if p.exists()]
    if not blueprints:
        raise ValueError("No blueprints to synthesize")

    # Auto-discover transcript files from sibling directories when not supplied
    if transcript_paths is None:
        transcript_paths = [p.parent / "transcript.json" for p in blueprint_paths]

    # Merge script_formula fields
    all_hooks = [b.get("script_formula", {}).get("hook_pattern", "") for b in blueprints]
    all_arcs = [b.get("script_formula", {}).get("arc_beats", []) for b in blueprints]
    all_rhythms = [b.get("script_formula", {}).get("sentence_rhythm", "") for b in blueprints]
    all_tones = [b.get("script_formula", {}).get("tone", "") for b in blueprints]
    all_vo_styles = [b.get("script_formula", {}).get("vo_style", "") for b in blueprints]

    # Merge pacing
    all_scene_lengths = [b.get("pacing_template", {}).get("avg_scene_length_s", 4.0) for b in blueprints]

    # Pick best blueprint (most complete scene_prompts) as structural template
    best = max(blueprints, key=lambda b: len(b.get("scene_prompts", [])))

    dna = {
        "source": "channel_dna_synthesis",
        "channel_name": channel_name,
        "num_videos": len(blueprints),
        "script_formula": {
            "hook_pattern": _most_common(all_hooks),
            "arc_beats": _flatten_unique(all_arcs),
            "sentence_rhythm": best.get("script_formula", {}).get("sentence_rhythm", {"avg_words": 12, "stdev": 4}),
            "tone": best.get("script_formula", {}).get("tone", ["authoritative"]),
            "vo_style": _most_common(all_vo_styles),
        },
        "pacing_template": {
            **best.get("pacing_template", {}),
            "avg_scene_length_s": round(statistics.mean(all_scene_lengths), 2),
        },
        # Structural shot language only — NO topic-specific image descriptions.
        "scene_composition": _extract_scene_composition(blueprints),
        "formula_metadata": best.get("formula_metadata", {}),
        # ── Visual style formula — topic-stripped aesthetic profile ────────────
        # Merged from all blueprint visual_style_formula fields.
        # Feeds image_prompt generation in script_gen so every frame looks
        # like the channel's aesthetic regardless of the new video's topic.
        "visual_style_formula": _merge_visual_style(blueprints),
        # ── Writing style examples — actual VO text from scraped videos ──────
        # These are STRUCTURAL examples of sentence rhythm, vocabulary, and
        # hook writing. The TOPIC is stripped mentally — only the STYLE is
        # reused. The script generator uses these as few-shot style samples.
        "writing_examples": _extract_writing_examples(blueprints, transcript_paths or []),
        # ── Title formula — patterns extracted from video titles ─────────────
        "title_formula": _extract_title_formula(blueprints),
        # ── Call-to-action patterns — the channel's typical closer CTAs ──────
        "call_to_action_examples": _extract_cta_examples(blueprints),
        # ── Deep writing DNA — full Claude linguistic analysis ───────────────
        # Explicit, actionable profile: hook formula, voice fingerprint,
        # sentence architecture, tension build, emotional arc, etc.
        # Used by script_gen.py as the primary style guide.
        "writing_dna": _extract_deep_writing_dna(blueprints, transcript_paths or []),
    }

    out_dir = DNA_DIR / channel_name
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "dna.json"
    out_path.write_text(json.dumps(dna, indent=2, ensure_ascii=False), encoding="utf-8")
    return out_path


def _merge_visual_style(blueprints: list[dict]) -> dict:
    """Merge visual_style_formula fields from N blueprints into a consensus.

    Picks the richest image_prompt_prefix (longest, most specific) and
    aggregates style_tags across all blueprints. Other text fields come from
    the blueprint whose visual_style_formula is most complete.
    """
    styles = [b.get("visual_style_formula") for b in blueprints
              if b.get("visual_style_formula")]
    if not styles:
        return {}

    # Pick the most complete style as the base
    best_style = max(styles, key=lambda s: len(s.get("image_prompt_prefix", "")))

    # Aggregate style_tags across all blueprints (deduplicated, most frequent first)
    tag_counts: dict[str, int] = {}
    for s in styles:
        for tag in s.get("style_tags", []):
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
    merged_tags = [t for t, _ in sorted(tag_counts.items(), key=lambda x: -x[1])][:8]

    # Aggregate avoid lists
    avoid: list[str] = []
    seen_avoid: set[str] = set()
    for s in styles:
        for item in s.get("avoid", []):
            if item not in seen_avoid:
                seen_avoid.add(item)
                avoid.append(item)

    return {
        **best_style,
        "style_tags": merged_tags,
        "avoid": avoid,
        "source_videos": len(styles),
    }


def _extract_scene_composition(blueprints: list[dict]) -> dict:
    """Extract STRUCTURAL shot vocabulary — camera moves + production types.

    This is topic-agnostic: it tells the script generator HOW the channel
    shoots (dolly_in 40% of the time, b_roll dominant, etc.) without
    carrying over any visual content from the reference topics.
    """
    camera_counts: dict[str, int] = {}
    prod_counts: dict[str, int] = {}
    scene_counts: list[int] = []

    for bp in blueprints:
        scenes = bp.get("scene_prompts", [])
        scene_counts.append(len(scenes))
        for sc in scenes:
            cm = sc.get("camera_move", "")
            if cm:
                camera_counts[cm] = camera_counts.get(cm, 0) + 1
            pt = sc.get("production_type", "")
            if pt:
                prod_counts[pt] = prod_counts.get(pt, 0) + 1

    total_cam = sum(camera_counts.values()) or 1
    total_prod = sum(prod_counts.values()) or 1

    return {
        "avg_scene_count": round(statistics.mean(scene_counts), 1) if scene_counts else 0,
        "camera_move_distribution": {k: round(v / total_cam, 2) for k, v in sorted(camera_counts.items(), key=lambda x: -x[1])},
        "production_type_distribution": {k: round(v / total_prod, 2) for k, v in sorted(prod_counts.items(), key=lambda x: -x[1])},
    }


def _clean_vo(text: str) -> str:
    """Strip HTML entities and normalise whitespace from transcript/VO text."""
    text = re.sub(r"&\w+;", " ", text)   # &nbsp; &amp; etc.
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _extract_writing_examples(blueprints: list[dict], transcript_paths: list[Path]) -> dict:
    """Pull real VO text + hook text as style samples for the script generator.

    Priority order:
      1. Full transcripts (best — sentence-level granularity, clean text)
      2. blueprint.script_formula.hook_text (first 15s hook)
      3. blueprint.scene_prompts[].vo_segment (fallback, often sparse)

    VISUAL FIREWALL: text only — no image_prompts, no scene descriptions,
    no character names. The consumer (script_gen) studies SENTENCE RHYTHM
    and VOCABULARY, never topic content.
    """
    hook_texts: list[str] = []
    vo_sentences: list[str] = []
    repro_notes: list[str] = []

    for bp in blueprints:
        sf = bp.get("script_formula") or {}
        hook = _clean_vo(sf.get("hook_text", ""))
        if hook:
            hook_texts.append(hook)

        note = (sf.get("reproducibility_notes") or "").strip()
        if note:
            repro_notes.append(note)

    # Pull VO from full transcripts — far more text than scene_prompts
    for tp in transcript_paths:
        if not tp or not tp.exists():
            continue
        try:
            segs = json.loads(tp.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(segs, list):
            continue
        for seg in segs:
            vo = _clean_vo(seg.get("text", ""))
            if len(vo) > 25:
                vo_sentences.append(vo)

    # Fallback: scene_prompts vo_segment if transcripts were empty
    if not vo_sentences:
        for bp in blueprints:
            for sc in bp.get("scene_prompts", []):
                vo = _clean_vo(sc.get("vo_segment", ""))
                if len(vo) > 20:
                    vo_sentences.append(vo)

    # Deduplicate while preserving order, cap totals
    seen: set[str] = set()
    deduped: list[str] = []
    for s in vo_sentences:
        key = s[:80]
        if key not in seen:
            seen.add(key)
            deduped.append(s)

    return {
        "hook_text_examples": hook_texts[:5],
        "vo_sentence_examples": deduped[:40],   # 40 sentences → rich style signal
        "reproducibility_notes": repro_notes[:3],
    }


def _extract_title_formula(blueprints: list[dict]) -> dict:
    """Analyze video titles from blueprints to extract structural title patterns.

    Looks at source.title in each blueprint. Returns format distributions,
    avg word count, and common structural patterns (number lists, questions,
    colon splits, how/why/what openers). Pure structure — no topic content.
    """
    titles: list[str] = []
    for bp in blueprints:
        t = (bp.get("source") or {}).get("title", "").strip()
        if t:
            titles.append(t)

    if not titles:
        return {}

    word_counts = [len(t.split()) for t in titles]
    formats: dict[str, int] = {
        "number_list": 0,    # starts with digit: "5 Ways to…"
        "question": 0,       # ends with ? or starts with How/Why/What/Which/When/Is/Are/Does/Did
        "colon_split": 0,    # contains " : " or " — " (reveal/contrast structure)
        "bracket_label": 0,  # contains [ ] or ( ) — e.g. "[Full Video]"
        "statement": 0,      # everything else — declarative
    }
    opener_words: dict[str, int] = {}

    QUESTION_STARTERS = {"how", "why", "what", "which", "when", "where", "is", "are", "does", "did", "can", "will", "should"}

    for t in titles:
        first_word = t.split()[0].lower().rstrip(",:?") if t.split() else ""
        opener_words[first_word] = opener_words.get(first_word, 0) + 1

        if re.match(r"^\d", t):
            formats["number_list"] += 1
        elif t.endswith("?") or first_word in QUESTION_STARTERS:
            formats["question"] += 1
        elif re.search(r"\s[:\-\—]\s", t) or ": " in t:
            formats["colon_split"] += 1
        elif re.search(r"[\[\(]", t):
            formats["bracket_label"] += 1
        else:
            formats["statement"] += 1

    n = len(titles)
    top_openers = sorted(opener_words.items(), key=lambda x: -x[1])[:8]

    return {
        "avg_title_words": round(statistics.mean(word_counts), 1),
        "format_distribution": {k: round(v / n, 2) for k, v in formats.items() if v > 0},
        "dominant_format": max(formats, key=formats.get),
        "common_opener_words": [w for w, _ in top_openers if _ > 0],
        "sample_titles": titles[:5],   # structural reference only
    }


def _extract_cta_examples(blueprints: list[dict]) -> list[str]:
    """Collect call_to_action text from each blueprint's script_formula.

    script_formula.py extracts this field but channel_dna_synth previously
    discarded it. These are saved so script_gen can mirror the channel's
    typical closer ask (subscribe nudges, comment prompts, etc.).
    """
    ctas: list[str] = []
    seen: set[str] = set()
    for bp in blueprints:
        cta = (bp.get("script_formula") or {}).get("call_to_action") or ""
        cta = cta.strip()
        key = cta[:120]
        if cta and key not in seen:
            seen.add(key)
            ctas.append(cta)
    return ctas[:6]   # keep up to 6 distinct CTA patterns


def _extract_deep_writing_dna(blueprints: list[dict],
                               transcript_paths: list[Path]) -> dict:
    """Run a full Claude linguistic analysis on the channel's VO text.

    Sends up to 3 transcripts (≤ 10 000 chars each) to Claude and returns
    an explicit, actionable JSON profile of the creator's writing style.
    Returns {} on any failure — callers treat empty as "no deep DNA yet".
    """
    from generators.gemini_text import generate_text

    # ── Collect transcript text ─────────────────────────────────────────
    blocks: list[str] = []
    for tp in transcript_paths[:3]:
        if not tp or not tp.exists():
            continue
        try:
            segs = json.loads(tp.read_text(encoding="utf-8"))
            if not isinstance(segs, list):
                continue
            text = " ".join(_clean_vo(seg.get("text", "")) for seg in segs)
            text = text[:10_000]
            if len(text) > 300:
                blocks.append(text)
        except Exception:  # noqa: BLE001
            continue

    # Fallback: scene vo_segment text when transcripts are missing
    if not blocks:
        for bp in blueprints[:3]:
            vos = [_clean_vo(sc.get("vo_segment", ""))
                   for sc in bp.get("scene_prompts", [])]
            text = " ".join(v for v in vos if len(v) > 20)[:5_000]
            if len(text) > 300:
                blocks.append(text)

    if not blocks:
        return {}

    transcript_text = ""
    for i, block in enumerate(blocks, 1):
        transcript_text += f"\n--- VIDEO {i} ---\n{block}\n"

    prompt = DEEP_WRITING_DNA_PROMPT.format(
        n_videos=len(blocks),
        transcript_text=transcript_text,
    )

    try:
        raw = generate_text(prompt, temperature=0.1)
        raw = raw.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw)
            raw = re.sub(r"\n?```$", "", raw)
        parsed = json.loads(raw.strip())
        return parsed if isinstance(parsed, dict) else {}
    except Exception:  # noqa: BLE001
        return {}


def _most_common(lst: list[str]) -> str:
    filtered = [x for x in lst if x]
    if not filtered:
        return ""
    return max(set(filtered), key=filtered.count)


def _flatten_unique(lists: list[list]) -> list:
    seen, out = set(), []
    for sub in lists:
        for item in sub:
            k = str(item)
            if k not in seen:
                seen.add(k)
                out.append(item)
    return out
