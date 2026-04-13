"""Hardcoded design rules from 1of10's 300K-video / 62B-views study (masterplan §24.4)."""
from __future__ import annotations

THUMBNAIL_DATA_RULES = {
    "text": {
        "optimal": "NO text or < 10 characters",
        "coverage": "< 7% of image area",
        "rule": "Use text ONLY to amplify emotion, never to explain the video",
    },
    "color": {
        "best_performing": ["cyan", "green", "yellow", "orange"],
        "cyan_boost": "+36% median views vs average",
        "rule": "Default to bright/vibrant; use dark ONLY for crime/noir niche",
    },
    "faces": {
        "rule_for_faceless": "Faceless channels NOT at a disadvantage; use objects, "
                             "environments, symbols, data viz, dramatic scenes",
    },
    "composition": {
        "focal_points": "1 dominant element max",
        "rule": "Reduce visual noise ruthlessly; viewer decides in <1 second",
    },
}

TITLE_DATA_RULES = {
    "length":   {"optimal_words": 5, "optimal_chars": 30},
    "sentiment":{"negative_boost": "+22% views", "rule": "Frame as threat/warning when possible"},
    "emotion":  {"top_performing": ["joy/funny", "anger", "controversy"]},
    "numbers":  {"finding": "-11% views with numbers in TITLE", "rule": "Numbers in THUMBNAIL good, in TITLE bad"},
    "readability": {"finding": "+20% views for high readability"},
}

CURIOSITY_GAP = {
    "rule": "Thumbnail and title are ONE UNIT — they must COMPLEMENT not REPEAT.",
    "bad":  "Title: '$2M AI Empire' + Thumbnail text: '$2M AI EMPIRE'",
    "good": "Title: '$2M AI Empire' + Thumbnail: dramatic visual + text: 'HOW?'",
}

ANTI_AI_DIRECTIVES = """\
CRITICAL — DO NOT VIOLATE:
- NO smooth plastic skin or perfect symmetry
- NO oversaturated candy colors or flat stock-photo lighting
- NO floating objects without grounding shadows
- NO concept-art / digital-illustration look
- INSTEAD: editorial photography feel, slight film grain, intentional
  imperfection, dramatic natural lighting, depth of field, real textures
- Must look human-designed, NOT AI-generated
"""


def rules_summary_for_prompt(niche: str) -> str:
    """Compact text block to inject into image prompts."""
    is_dark = "crime" in niche.lower() or "noir" in niche.lower()
    color_line = ("Dark palette with one color pop (red/orange accent)" if is_dark
                  else "Cyan/green/yellow accents preferred (+36% views in study)")
    return (
        "DATA-BACKED RULES (62B views study):\n"
        f"- Color: {color_line}. Brighter outperforms darker except crime/noir.\n"
        "- Text: <10 chars, <7% of image area, or NO text. Upper third placement.\n"
        "- One focal point. Viewer decides in <1s. Mobile-readable at 160px.\n"
        f"{ANTI_AI_DIRECTIVES}"
    )
