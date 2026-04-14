"""Channel text DNA extraction + channel-native hook generation.

The old `extract_hook()` was regex-based keyword fishing. It produced generic
text like "EXPOSED" or "REVEALED" regardless of channel, and it didn't
understand the channel's actual typographic voice.

This module:
  1. Reads the channel's cached thumbnails via Gemini Vision to extract the
     ACTUAL text that appears on them — the words creator uses, how they
     structure it (one-line vs two-line), casing, tone, typical length.
  2. Uses that DNA plus the video title to generate a hook that feels native
     to the channel — not a title regurgitation.

Cached per channel in the `channel_briefs` table (new `text_dna` column).
"""
from __future__ import annotations

import base64
import datetime as dt
import json
import re
from pathlib import Path

import httpx

from cli import config as cfg
from data.db import db
from generators.gemini_text import generate_text

VERTEX_HOST = "https://aiplatform.googleapis.com"
ENDPOINT_TMPL = "/v1/publishers/google/models/{model}:generateContent"


TEXT_DNA_PROMPT = """\
You are analyzing the TEXT that appears on YouTube thumbnails from one creator.

I'm showing you {count} of this creator's thumbnails. Look ONLY at the text
baked into each image (titles, captions, labels, numbers). Ignore visual
style — another analyst handles that.

For EACH thumbnail, transcribe the visible text exactly as it appears
(preserve casing, line breaks, punctuation, numbers). If a thumbnail has
no prominent baked-in text — or only tiny marginal labels — write "[none]"
for that entry.

Then decide overall TEXT USAGE for this channel, one of:
- "never"     — essentially none of the thumbnails use baked-in text
- "rare"      — maybe 1 in 5 uses text, usually goes text-free
- "sometimes" — roughly half use text, half don't
- "often"     — most use text but some are clean
- "always"    — every thumbnail has prominent text

Then synthesize a TEXT DNA profile with:

1. STRUCTURE: Is text usually one block, two stacked blocks, a label + big
   word, etc? What's the typical layout?
2. LENGTH: Average words per block. Shortest and longest seen.
3. CASING: ALL CAPS, Title Case, mixed? Any signature casing move?
4. VOCABULARY TONE: What register? (shock / deadpan / financial-jargon /
   conversational / clickbait-reaction / editorial-deadpan / etc.)
5. RECURRING WORDS: Actual words that appear more than once across these
   thumbnails — e.g. "NOBODY", "BROKE", "CRASHED", "SECRET".
6. PUNCTUATION/SYMBOLS: Question marks? Dollar signs? Arrows? None?
7. COMPLEMENT vs REPEAT: Does the text typically COMPLEMENT the video's
   implied title (adding a reaction / stakes / tease) or REPEAT it?
8. "GENERATE LIKE THIS" RULE: In one sentence, how should a new hook be
   written to fit this channel's voice?

Output STRICT JSON only, this schema:
{{
  "text_usage": "never|rare|sometimes|often|always",
  "observed_texts": ["...", "[none]", "...", ...],
  "structure": "...",
  "length": "...",
  "casing": "...",
  "tone": "...",
  "recurring_words": ["...", "..."],
  "punctuation": "...",
  "complement_pattern": "...",
  "generation_rule": "..."
}}

No prose, no markdown fence, just the JSON.
"""


HOOK_PROMPT = """\
You are writing the TEXT overlay for a YouTube thumbnail, in the voice of a
specific channel. Do this in three steps.

═══════════════════════════════════════════
STEP 1 — DECODE THE TITLE'S THESIS.
═══════════════════════════════════════════
What STANCE is the creator taking? Do NOT just identify the topic.

Ask yourself:
- Is it a CRITIQUE / TAKEDOWN? (title signals something is bad)
- An EXPOSÉ / REVELATION? (hidden truth, secret)
- A WARNING / CAUTIONARY tale? (danger, trap)
- A SUCCESS / FLEX story? (achievement, win)
- A REGRET / CONFESSION? (admitting mistake)
- A PREDICTION / DOOM call? (future collapse)
- A TEACHING / ANALYSIS? (neutral-explanatory)
- A CHALLENGE / PROVOCATION? (controversial claim)

Examples of decoding:
- "LinkedIn is a horrible place"  →  CRITIQUE: LinkedIn is cringe / toxic / fake
- "The secret behind NFTs"         →  EXPOSÉ: NFTs hide something
- "Never buy a Tesla"              →  WARNING: Tesla is a trap
- "How I made $10k"                →  SUCCESS: specific financial win
- "AI is replacing us"             →  DOOM: we're cooked
- "I was wrong about crypto"       →  CONFESSION: changed mind

═══════════════════════════════════════════
STEP 2 — MATCH THE CHANNEL'S VOICE.
═══════════════════════════════════════════
Below is the channel's ACTUAL text DNA — the words they really use, their
structure, their casing, their tone.

CHANNEL'S TEXT DNA:
{text_dna}

═══════════════════════════════════════════
STEP 3 — WRITE THE HOOK.
═══════════════════════════════════════════
The hook must REINFORCE the thesis from Step 1, in the voice from Step 2.

HARD RULES:
1. LANGUAGE: Write the hook in the SAME LANGUAGE as the video title above.
   If the title is English, write in English. If it's French, write in
   French. If it's German, write in German. The channel's DNA may show
   words in a different language — IGNORE the channel's language, only
   borrow its STRUCTURE, CASING, LENGTH, and TONE. Never output a hook in
   a language different from the title.

2. NEVER just label the topic. These are all BAD:
   - Title "LinkedIn is horrible"  →  "PROFESSIONAL NETWORK"   ← labels topic
   - Title "AI is replacing us"    →  "ARTIFICIAL INTELLIGENCE" ← labels topic
   - Title "Never buy Tesla"       →  "ELECTRIC CAR"           ← labels topic
   - Title "NFTs explained"        →  "NFTS"                    ← labels topic

3. The hook IS the creator's REACTION / VERDICT / STAKES, not a caption of
   the subject. These are GOOD:
   - Title "LinkedIn is horrible"  →  "CORPORATE HELL"  or  "IT'S CRINGE"
   - Title "AI is replacing us"    →  "WE'RE COOKED"    or  "GAME OVER"
   - Title "Never buy Tesla"       →  "THE TRAP"        or  "WE GOT SCAMMED"
   - Title "Secret behind NFTs"    →  "THE TRUTH"       or  "IT'S A LIE"

4. COMPLEMENT the title — if the title already says "horrible", your hook
   shouldn't also say "horrible". Pick a DIFFERENT angle of the same thesis
   (stakes, reaction, verdict, emotion).

5. Match the channel's STRUCTURE (one block vs two stacked blocks — use \\n
   between lines if two), CASING, LENGTH, TONE — but TRANSLATE the style
   into the title's language. Do NOT copy the channel's exact recurring
   words if they're in a different language than the title.

6. Use the channel's RECURRING WORDS only when they're in the title's
   language AND they fit the thesis. If the channel speaks German and
   your title is English, do not use the German words — use equivalently
   punchy English words in the same register.

7. No emojis. No quotes around your output. No "Hook:" prefix.

═══════════════════════════════════════════
INPUT
═══════════════════════════════════════════
VIDEO TITLE: "{title}"
{hook_extra}

═══════════════════════════════════════════
OUTPUT
═══════════════════════════════════════════
Only the text that appears on the thumbnail. Nothing else.
"""


HOOK_MULTI_PROMPT = """\
You are writing {n} DIFFERENT thumbnail text overlays for the SAME video, in
the voice of ONE specific channel. Each overlay will be paired with a
different visual variant, so the overlays themselves must be different too.

═══════════════════════════════════════════
STEP 1 — DECODE THE TITLE'S THESIS.
═══════════════════════════════════════════
What STANCE is the creator taking? Do NOT just identify the topic.
- CRITIQUE / TAKEDOWN, EXPOSÉ / REVELATION, WARNING, SUCCESS / FLEX,
  REGRET / CONFESSION, PREDICTION / DOOM, TEACHING, PROVOCATION.

Examples:
- "LinkedIn is a horrible place"  →  CRITIQUE: LinkedIn is cringe / toxic
- "Secret behind NFTs"             →  EXPOSÉ: NFTs hide something
- "Never buy a Tesla"              →  WARNING: Tesla is a trap

═══════════════════════════════════════════
STEP 2 — CHANNEL'S TEXT DNA.
═══════════════════════════════════════════
{text_dna}

═══════════════════════════════════════════
STEP 3 — WRITE {n} DIFFERENT HOOKS.
═══════════════════════════════════════════
Each hook hits a DIFFERENT angle of the same thesis. Mix the angles:
- Angle 1: VERDICT (declarative judgement) — e.g. "IT'S A TRAP"
- Angle 2: STAKES (what's at risk / what you lose) — e.g. "YOU'RE COOKED"
- Angle 3: REVEAL (teasing hidden truth) — e.g. "THE TRUTH"
- Angle 4: REACTION (emotional response) — e.g. "NEVER AGAIN"
- Or: confession, dare, warning label, rhetorical question, specific number.

HARD RULES (apply to ALL hooks):
1. LANGUAGE: Write every hook in the SAME LANGUAGE as the video title.
   If the channel's DNA is in a different language, ignore the channel's
   exact words — only borrow its STRUCTURE, CASING, and TONE, rendered in
   the title's language. Never mix languages. Never output a hook in a
   language different from the title.
2. NEVER label the topic. "PROFESSIONAL NETWORK" for LinkedIn is DUMB.
   The hook is the creator's REACTION / STAKES / VERDICT, not the subject.
3. COMPLEMENT the title — don't reuse its main words.
4. Match the channel's STRUCTURE, CASING, LENGTH, TONE (in the title's
   language).
5. Use the channel's recurring words ONLY if they're in the title's
   language AND they fit. Otherwise find equivalents in the title's
   language with the same register.
6. The {n} hooks must be visibly DIFFERENT from each other — different
   angle, different vocabulary, different length if the channel allows.
7. If the channel's DNA uses two-line stacked text, format each hook with
   a single \\n separator inside the string.
8. No emojis.

═══════════════════════════════════════════
INPUT
═══════════════════════════════════════════
VIDEO TITLE: "{title}"

═══════════════════════════════════════════
OUTPUT
═══════════════════════════════════════════
Output STRICT JSON: an array of exactly {n} strings. Nothing else.
No prose, no markdown fence, no labels. Example shape:
["HOOK ONE", "HOOK TWO", "HOOK THREE"]
"""


def _ensure_text_dna_column() -> None:
    d = db()
    if "channel_briefs" not in d.table_names():
        # The style_channel module creates it lazily; don't fight.
        return
    cols = {c.name for c in d["channel_briefs"].columns}
    if "text_dna" not in cols:
        d["channel_briefs"].add_column("text_dna", str)


def build_text_dna(channel_id: str, thumb_paths: list[Path]) -> str:
    """Return the cached text DNA JSON string for this channel.

    Builds it via Gemini Vision if not cached. Returns empty string on any
    failure — callers treat missing DNA as a signal to fall back to the old
    regex hook.
    """
    _ensure_text_dna_column()
    d = db()

    existing = None
    if "channel_briefs" in d.table_names():
        try:
            existing = d["channel_briefs"].get(channel_id)
        except Exception:  # noqa: BLE001
            existing = None

    if existing and existing.get("text_dna") and existing.get("thumb_count") == len(thumb_paths):
        # Only reuse if the cached DNA already has the new text_usage field.
        # Older DNAs predate the qualitative usage signal — force rebuild.
        try:
            parsed = json.loads(existing["text_dna"])
            if "text_usage" in parsed:
                return existing["text_dna"] or ""
        except Exception:  # noqa: BLE001
            pass

    if not thumb_paths:
        return ""

    api_key = cfg.get("vertex.api_key")
    model = cfg.get("gemini.vision_model", "gemini-2.5-pro")
    url = f"{VERTEX_HOST}{ENDPOINT_TMPL.format(model=model)}?key={api_key}"

    parts: list[dict] = []
    for p in thumb_paths[:8]:
        parts.append({"inlineData": {
            "data": base64.b64encode(p.read_bytes()).decode(),
            "mimeType": "image/jpeg",
        }})
    parts.append({"text": TEXT_DNA_PROMPT.format(count=len(thumb_paths[:8]))})

    try:
        with httpx.Client(timeout=120.0) as c:
            resp = c.post(url, json={
                "contents": [{"role": "user", "parts": parts}],
                "generationConfig": {"responseModalities": ["TEXT"], "temperature": 0.2},
            }, headers={"Content-Type": "application/json"})
        if resp.status_code >= 300:
            return ""
        payload = resp.json()
        texts: list[str] = []
        for cand in payload.get("candidates", []):
            for part in (cand.get("content") or {}).get("parts", []):
                if "text" in part:
                    texts.append(part["text"])
        raw = "\n".join(texts).strip()
        raw = _strip_fence(raw)
        # Validate it's parseable JSON — if not, discard
        try:
            json.loads(raw)
        except Exception:  # noqa: BLE001
            return ""
    except Exception:  # noqa: BLE001
        return ""

    if raw and "channel_briefs" in d.table_names():
        try:
            d["channel_briefs"].upsert({
                "channel_id": channel_id,
                "text_dna": raw,
                "text_dna_built_at": dt.datetime.now(dt.UTC).isoformat(),
            }, pk="channel_id", alter=True)
        except Exception:  # noqa: BLE001
            pass
    return raw


def generate_smart_hook(title: str, text_dna: str,
                          prefer_no_text: bool = False) -> str:
    """Generate a channel-native thumbnail hook. Empty string if DNA missing
    or generation fails — caller falls back to regex extract_hook."""
    if not text_dna:
        return ""
    extra = ""
    if prefer_no_text:
        extra = "\nNOTE: The user requested NO text. Return an empty string.\n"

    prompt = HOOK_PROMPT.format(
        text_dna=text_dna, title=title.strip(), hook_extra=extra,
    )
    try:
        raw = generate_text(prompt, temperature=0.75).strip()
    except Exception:  # noqa: BLE001
        return ""

    return _clean_hook(raw)


def generate_smart_hooks(title: str, text_dna: str, n: int = 4) -> list[str]:
    """Generate N DISTINCT channel-native hooks, one per variant.

    Each hook captures a DIFFERENT angle of the title's thesis (stakes,
    reaction, verdict, emotion, provocation). Returns up to N cleaned
    hooks. Returns [] on failure so caller can fall back.
    """
    if not text_dna or n <= 0:
        return []
    prompt = HOOK_MULTI_PROMPT.format(
        text_dna=text_dna, title=title.strip(), n=n,
    )
    try:
        raw = generate_text(prompt, temperature=0.9).strip()
    except Exception:  # noqa: BLE001
        return []
    raw = _strip_fence(raw)
    import json as _json
    try:
        items = _json.loads(raw)
    except Exception:  # noqa: BLE001
        # Model didn't output JSON — try to split by lines as last resort
        items = [ln for ln in raw.splitlines() if ln.strip()]
    cleaned: list[str] = []
    for item in items[:n]:
        h = _clean_hook(str(item))
        if h and h not in cleaned:
            cleaned.append(h)
    # Pad with None-equivalent if model returned fewer than n — caller handles
    return cleaned


def get_text_usage(text_dna: str) -> str:
    """Return the channel's qualitative text-usage label.

    One of: "never", "rare", "sometimes", "often", "always".
    Falls back to "sometimes" if the DNA is missing/unparseable or doesn't
    specify — a neutral default that lets both text and text-free variants
    appear when the user requests many.
    """
    if not text_dna:
        return "sometimes"
    import json as _json
    try:
        d = _json.loads(text_dna)
    except Exception:  # noqa: BLE001
        return "sometimes"

    explicit = str(d.get("text_usage", "")).strip().lower()
    if explicit in {"never", "rare", "sometimes", "often", "always"}:
        return explicit

    # Fallback: infer from observed_texts array (old DNAs without text_usage)
    observed = d.get("observed_texts") or []
    if not isinstance(observed, list) or not observed:
        return "sometimes"
    total = len(observed)
    none_like = sum(
        1 for t in observed
        if not t or str(t).strip().lower() in {"[none]", "none", "n/a", "-", ""}
    )
    rate = (total - none_like) / total
    if rate <= 0.1:   return "never"
    if rate <= 0.35:  return "rare"
    if rate <= 0.65:  return "sometimes"
    if rate <= 0.9:   return "often"
    return "always"


def plan_text_slots(text_usage: str, n_variants: int,
                     user_forced_no_text: bool = False) -> list[bool]:
    """Decide which variants (by index) should have text rendered.

    Returns a list of booleans, length n_variants. True = this variant
    renders a hook, False = this variant is text-free. Interleaved so the
    user sees a visible mix in the grid.

    Rules:
      - user_forced_no_text → every slot False.
      - "never"     → 0 slots with text.
      - "rare"      → 1 slot (≤ 25%) if n_variants >= 2, else 0.
      - "sometimes" → ~50%, rounded up.
      - "often"     → ~75%, at least one text-free if n_variants >= 2.
      - "always"    → every slot True.
    """
    if user_forced_no_text or n_variants <= 0:
        return [False] * max(0, n_variants)

    if text_usage == "never":
        count = 0
    elif text_usage == "always":
        count = n_variants
    elif text_usage == "rare":
        count = 1 if n_variants >= 2 else 0
    elif text_usage == "sometimes":
        count = (n_variants + 1) // 2  # round up (4→2, 3→2, 5→3)
    elif text_usage == "often":
        count = max(1, (n_variants * 3 + 3) // 4)  # ~75%, keep ≥1 text-free when possible
        if n_variants >= 2 and count >= n_variants:
            count = n_variants - 1
    else:
        count = (n_variants + 1) // 2

    if count <= 0:
        return [False] * n_variants
    if count >= n_variants:
        return [True] * n_variants

    # Interleave: spread `count` True slots evenly across n_variants
    slots = [False] * n_variants
    step = n_variants / count
    for k in range(count):
        idx = int(k * step)
        if idx < n_variants:
            slots[idx] = True
    # Safety: if rounding underfilled, fill next available
    while sum(slots) < count:
        for i in range(n_variants):
            if not slots[i]:
                slots[i] = True; break
    return slots


def _clean_hook(raw: str) -> str:
    raw = raw.strip().strip('"').strip("'")
    raw = re.sub(r"^(hook|text|output|answer)\s*[:\-]\s*", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"\n+", "\n", raw).strip()
    if len(raw) > 80:
        raw = raw[:80].rstrip()
    return raw


def _strip_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    m = re.search(r"\{.*\}", text, re.DOTALL)
    return m.group(0) if m else text
