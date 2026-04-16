"""Unified style resolution — handles all three style types.

style_id formats:
  "dna:UCxxxxxx"          → resolve via resolve_style_channel()
  "preset:<slug>"         → return hardcoded preset definition
  "custom:<uuid4>"        → load from styles table + local images
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DATA_ROOT = Path(__file__).resolve().parent.parent / "data"
CUSTOM_STYLES_DIR = DATA_ROOT / "custom_styles"


@dataclass
class StyleResult:
    """Result of resolving any style_id."""
    style_brief: str              # 300-400 word brief for Gemini prompt
    reference_images: list[Path]  # 0-N image paths (pipeline clips to 2)
    image_prompt_prefix: str      # prepended to every image_gen prompt
    text_dna: str                 # JSON string, empty for preset/custom
    label: str                    # human-readable name for logging


# ── Preset definitions ────────────────────────────────────────────────────────
PRESETS: dict[str, dict[str, str]] = {
    "comic-book": {
        "name": "Comic Book",
        "image_prompt_prefix": (
            "Bold comic book illustration style, thick black ink outlines, "
            "halftone dot shading, flat saturated colors, dynamic action lines, "
            "vintage four-color print aesthetic, speech bubble typography if text present."
        ),
        "style_brief": (
            "Render in the visual language of classic American comic books. "
            "Use thick ink outlines on every element, halftone dot patterns for shading, "
            "a restricted palette of flat saturated primaries, and strong diagonal action lines. "
            "Faces should be expressive and slightly exaggerated. Backgrounds should feel "
            "illustrated, not photographic. If text is included, letter it in bold hand-drawn caps."
        ),
    },
    "anime": {
        "name": "Anime",
        "image_prompt_prefix": (
            "Anime illustration style, crisp cel-shading, large expressive eyes, "
            "vibrant saturated palette, speed lines, dramatic lighting with rim light glow, "
            "clean linework, cinematic 16:9 composition."
        ),
        "style_brief": (
            "Render in high-quality anime key-visual style. Cel-shaded coloring with "
            "strong specular highlights, large emotive eyes, dynamic composition with "
            "speed lines or environmental effects. Color palette should be vivid and "
            "high-contrast. Lighting should be dramatic with coloured rim lights. "
            "Character anatomy should follow anime proportion conventions."
        ),
    },
    "pixel-art": {
        "name": "Pixel Art",
        "image_prompt_prefix": (
            "Retro pixel art style, 32x32 to 64x64 sprite scale, limited 16-color palette, "
            "dithering for gradients, chunky pixels, no anti-aliasing, isometric or side-view."
        ),
        "style_brief": (
            "Render as authentic pixel art. Use a limited palette of 16-32 colors maximum. "
            "Every pixel must be intentional — no anti-aliasing or sub-pixel rendering. "
            "Use dithering patterns for gradients. Scale should suggest 32-64px sprites "
            "upscaled cleanly. Composition should read clearly at small sizes. "
            "Isometric perspective preferred for scenes."
        ),
    },
    "pixar": {
        "name": "Pixar",
        "image_prompt_prefix": (
            "Pixar-style 3D animation render, subsurface scattering skin, "
            "warm soft ambient occlusion, slightly exaggerated proportions, "
            "rich physically-based materials, cinematic depth of field, "
            "cheerful high-key lighting."
        ),
        "style_brief": (
            "Render in the visual style of Pixar feature films. Use 3D CG aesthetics with "
            "subsurface scattering on skin, physically-based materials with micro-detail, "
            "warm three-point lighting with a strong key and subtle fill, and shallow cinematic "
            "depth of field. Character proportions should be slightly exaggerated — big eyes, "
            "expressive faces. Color palette should be rich and saturated with careful "
            "complementary accent colors."
        ),
    },
    "digital-art": {
        "name": "Digital Art",
        "image_prompt_prefix": (
            "Professional digital painting, painterly brush strokes, rich color blending, "
            "dramatic chiaroscuro lighting, detailed textures, concept-art level finish, "
            "matte painting quality."
        ),
        "style_brief": (
            "Render as high-end digital painting / concept art. Use loose but confident "
            "painterly brush strokes with visible texture. Dramatic chiaroscuro lighting with "
            "strong highlights and deep shadows. Color palette should favor warm-cool contrast. "
            "Level of finish should match professional concept art or matte painting — "
            "detailed in focal areas, looser at edges."
        ),
    },
    "watercolor": {
        "name": "Watercolor",
        "image_prompt_prefix": (
            "Soft watercolor illustration, wet-on-wet bleeds, granulation texture, "
            "translucent layered washes, white paper showing through, "
            "organic irregular edges, muted desaturated palette."
        ),
        "style_brief": (
            "Render as a traditional watercolor painting. Use wet-on-wet color blooms, "
            "granulation texture in shadow areas, translucent layered washes with the "
            "white of the paper showing through in highlights. Edges should be soft and "
            "irregular. Palette should be desaturated and harmonious — avoid vivid digital "
            "saturation. Subjects should look hand-painted, not photographic."
        ),
    },
    "low-poly": {
        "name": "Low Poly",
        "image_prompt_prefix": (
            "Low-poly geometric 3D art, flat-shaded triangulated facets, "
            "pastel or vivid geometric palette, clean hard edges between facets, "
            "no textures or gradients within each polygon, abstract geometric aesthetic."
        ),
        "style_brief": (
            "Render as low-poly geometric art. Decompose every shape into visible flat-shaded "
            "triangular facets. No smooth gradients or textures within individual polygons. "
            "Palette should use clean geometric color blocking — either pastel or bold, "
            "but always flat within each facet. Hard edges between facets with no anti-aliasing "
            "blur. The aesthetic should feel modern and vector-adjacent."
        ),
    },
    # ── 20 NEW PRESET STYLES (AI-generatable, Gemini-optimized) ─────────────
    "ms-paint-dark": {
        "name": "MS Paint Dark Illustrated",
        "image_prompt_prefix": (
            "MS Paint-style digital illustration, rough painted brushstroke outlines, "
            "dark near-black background, colorful flat illustrated subject centered, "
            "lo-fi hand-painted texture, bold white shock-value text space, high contrast, 16:9."
        ),
        "style_brief": (
            "Render in the visual style of The Paint Explainer YouTube channel. Dark charcoal "
            "or near-black background dominates the frame. The central subject — a creature, "
            "phenomenon, or person — is rendered with rough, thick brushstroke outlines as if "
            "drawn in MS Paint, with flat bright colors (reds, yellows, blues) and no gradients "
            "or shading. The subject is bold and centered with plenty of contrast against the "
            "dark background. Leave clear negative space at top or bottom for large white text "
            "overlay. The mood is curious, slightly disturbing, and visually arresting. Style "
            "must feel handmade and non-corporate. No photorealism."
        ),
    },
    "simple-2d-narrative": {
        "name": "Simple 2D Illustrated Narrative",
        "image_prompt_prefix": (
            "Simple flat 2D illustration, slightly crude hand-drawn character style, "
            "clean flat color background, single illustrated character in expressive pose, "
            "limited 3-4 color palette, storybook-quality line art, bold sans-serif title text space, 16:9."
        ),
        "style_brief": (
            "Render in the style of Simple Paint and Wallace Animation YouTube channels. "
            "A single illustrated character takes center stage, drawn in a clean but slightly crude "
            "hand-drawn style — simplified anatomy, expressive pose, period-appropriate costume if "
            "historical. The background is a flat wash of 1-2 colors representing the setting "
            "(white, warm beige, a single environmental color). The palette is intentionally limited "
            "to 3-4 colors total. Character outlines are clean and confident. The overall feel is a "
            "textbook illustration come to life — accessible, not corporate. Leave space for bold "
            "series-format title text (e.g. 'Why It Sucks To Be A...'). No photorealism, no gradients, "
            "no busy backgrounds."
        ),
    },
    "stickman-historical": {
        "name": "Stickman Historical POV",
        "image_prompt_prefix": (
            "Stick figure illustration on white or minimal background, simple black line stick "
            "figure character in period-accurate historical costume, expressive exaggerated pose, "
            "flat minimal color accents only on costume elements, clean white space, bold title "
            "text area, 16:9."
        ),
        "style_brief": (
            "Render in the style of Bernard Animation and StickTory YouTube channels. The hero "
            "element is a classic stick figure — simple circle head, line body, four stick limbs — "
            "but dressed in historically accurate costume elements (armor, robes, uniform) rendered "
            "as flat color shapes layered over the stick body. Background is white or a single flat "
            "color wash. The stick figure must be in an expressive, narrative pose: defeated, "
            "triumphant, terrified, laboring. Maximum 3 colors used in the whole image. The "
            "composition should feel like a single storyboard panel. Leave top area clear for "
            "'Why It Sucks To Be A [X]' or 'POV: You Are A [X]' title format. Deliberately simple "
            "— the simplicity IS the brand."
        ),
    },
    "minimalist-animatic": {
        "name": "Minimalist 2D Animatic",
        "image_prompt_prefix": (
            "Rough storyboard animatic style, thick black ink outlines on white background, "
            "simplified human figures with exaggerated expressions, single frozen action frame, "
            "no color fills except occasional flat accent, sketch energy, FlipaClip aesthetic, 16:9."
        ),
        "style_brief": (
            "Render in the style of Rico Animations — a minimalist 2D animatic frozen frame. "
            "Characters are simplified human forms with thick black outlines, slightly more body "
            "definition than pure stick figures but no detailed anatomy. The single frame captures "
            "a comedic or dramatic peak moment — characters mid-action, mid-expression, mid-reaction. "
            "Background is white or near-white with minimal environmental line art if needed. Color "
            "is used sparingly: one or two flat accent colors maximum. The overall feel is a "
            "hand-drawn storyboard panel, not a finished illustration. Exaggerated expressions and "
            "dynamic poses are essential. Think FlipaClip frame-by-frame energy captured in a single image."
        ),
    },
    "finance-stickman": {
        "name": "Finance Stickman",
        "image_prompt_prefix": (
            "Pure black stick figure on white or solid single-color background, classic stick man "
            "in relatable financial scenario (crying at stock chart, running from debt monster, "
            "holding money bag), one red or green accent color only, bold financial hook text space, "
            "clean minimal composition, 16:9."
        ),
        "style_brief": (
            "Render as a finance-niche stickman YouTube thumbnail. The central character is a "
            "classic black stick figure — circle head, line body, four stick limbs — in a scenario "
            "that visualizes a financial concept or relatable money struggle: staring at a crashing "
            "red chart, running from a giant debt monster, celebrating with a green upward arrow, "
            "drowning in credit cards. Background is white or a single flat solid color. Only one "
            "accent color allowed beyond black and white — red for loss/danger, green for gain/success. "
            "No textures, no gradients, no complexity. The image must read clearly as a thumbnail at "
            "very small sizes. Leave generous space for a bold provocative financial headline."
        ),
    },
    "fern-3d-documentary": {
        "name": "Fern 3D Documentary",
        "image_prompt_prefix": (
            "Blender-style 3D render, smooth featureless humanoid figure with matte gray-white "
            "material, no facial details, stark directional lighting casting hard shadows, cold "
            "desaturated color palette, minimal cinematic composition, shallow depth of field, "
            "blurred environment, ultra-clean surfaces, 16:9."
        ),
        "style_brief": (
            "Render in the visual style of Fern and Hoog YouTube — the gold standard of faceless "
            "3D documentary aesthetics. The central figure is a smooth, featureless humanoid with "
            "matte gray-white or off-white material — no eyes, no mouth, no seams. Lighting is harsh "
            "and directional, casting one strong stark shadow. The color palette is cold: concrete "
            "grays, cool blues, white. Backgrounds are blurred or near-abstract environments that "
            "suggest location without showing detail. The mood is deliberately austere, serious, and "
            "cinematic. No warmth, no friendliness — this is investigative documentary visual language. "
            "Camera angle should feel like a slow cinematic zoom or push. Single clear focal point."
        ),
    },
    "dark-cinematic-noir": {
        "name": "Dark Cinematic Neo-Noir",
        "image_prompt_prefix": (
            "Dark cinematic composite, dramatic subject centered in spotlight, deep black background, "
            "atmospheric fog or rain, desaturated high-contrast color grade, crashing financial chart "
            "or data overlay, neo-noir investigative mood, bold white headline text space, 16:9."
        ),
        "style_brief": (
            "Render in the style of MagnatesMedia YouTube — business empire rise-and-fall documentary "
            "aesthetics. The frame is dominated by near-black with a single dramatic spotlight on the "
            "central subject (a person, building, or corporate symbol). Atmospheric fog, rain, or "
            "smoke adds depth. Color palette is heavily desaturated with one accent — typically red "
            "for crisis, gold for wealth. If financial data is included, charts should appear to be "
            "crashing downward with ominous red lines. The overall mood is: betrayal, collapse, "
            "investigation. The thumbnail should feel like a movie poster for a financial thriller. "
            "Maximum gravitas."
        ),
    },
    "gothic-horror": {
        "name": "Dark Fantasy Gothic Horror",
        "image_prompt_prefix": (
            "Gothic horror scene, Victorian haunted interior or exterior, candlelight as primary "
            "illumination, twisted baroque architecture with decay, deep navy and black palette with "
            "amber candlelight accents, atmospheric fog at ground level, dark fantasy illustration "
            "quality, cinematic dread, 16:9."
        ),
        "style_brief": (
            "Render in a dark fantasy gothic horror style. Architecture is Victorian or baroque but "
            "decayed — crumbling stone, peeling wallpaper, collapsed ceilings. The primary light "
            "source is candlelight: warm amber points of light pushing against overwhelming darkness. "
            "Deep navy, black, and charcoal dominate with amber as the only warm accent. Ground-level "
            "fog adds atmosphere. Subject matter leans toward haunted locations, shadowy figures, "
            "cursed objects, or supernatural entities barely visible in shadow. The mood must feel "
            "like genuine dread — not Halloween camp. Professional horror illustration quality."
        ),
    },
    "lovecraftian-horror": {
        "name": "Cosmic Horror / Lovecraftian",
        "image_prompt_prefix": (
            "Lovecraftian cosmic horror, eldritch entity of incomprehensible scale, deep ocean or "
            "void setting, bioluminescent accents on dark teal-black background, tiny human figures "
            "for scale contrast, forbidden geometry, overwhelming existential dread atmosphere, "
            "painterly horror illustration, 16:9."
        ),
        "style_brief": (
            "Render in Lovecraftian cosmic horror style. The defining characteristic is incomprehensible "
            "scale: a vast entity — tentacled, geometric, unknowable — dwarfs any human elements in frame. "
            "Setting is deep ocean, starless void, or ancient impossible architecture. Color palette is "
            "dark teal, deep purple, and absolute black with bioluminescent accents (glowing greens, "
            "electric blues) that suggest the entity's wrongness. Human figures, if present, should be "
            "tiny — emphasizing the viewer's insignificance. Atmosphere must convey that this thing should "
            "not exist. Painterly quality with deliberate unsettling geometry."
        ),
    },
    "dark-academia-mystery": {
        "name": "Dark Academia / Ancient Mysteries",
        "image_prompt_prefix": (
            "Ancient stone library or chamber interior, floating glowing manuscripts or sacred geometry "
            "symbols, warm amber candlelight on aged stone surfaces, dust motes in light beams, dark gold "
            "and sepia palette, hidden knowledge aesthetic, cinematic shadows, 16:9."
        ),
        "style_brief": (
            "Render in dark academia / ancient mysteries visual style. The setting is always interior — "
            "a stone library, underground chamber, or crypt filled with manuscripts, artifacts, and symbols. "
            "Warm amber candlelight is the primary light source, creating pools of illumination surrounded "
            "by deep shadow. Dust particles float visibly in shafts of light from above. Sacred geometry, "
            "runes, or cryptic symbols appear carved in stone or glowing on floating parchment. The color "
            "palette is sepia, dark gold, and aged stone gray. The mood is: forbidden knowledge that humanity "
            "was not meant to find. Intellectual gravitas meets supernatural dread."
        ),
    },
    "folk-horror-occult": {
        "name": "Folk Horror / Occult Ritual",
        "image_prompt_prefix": (
            "Folk horror ritual scene, ancient stone circle under blood moon, robed figures in dense fog, "
            "torch fire as primary light, blood red and deep shadow palette, primitive carved symbols, "
            "isolated rural setting, ominous supernatural atmosphere, 16:9."
        ),
        "style_brief": (
            "Render in folk horror and occult ritual visual style. The scene centers on a megalithic stone "
            "circle or ancient ritual site. Robed or masked figures form patterns in thick ground fog. The "
            "blood moon is the primary overhead light source, casting everything in red. Torch or bonfire "
            "light adds secondary warm illumination. Primitive symbols are carved into standing stones. The "
            "setting is deliberately isolated: open moorland, deep forest clearing, cliff edge. The mood is: "
            "ancient evil that was here long before civilization and will remain after. No modern elements. "
            "Rural isolation is essential to the dread."
        ),
    },
    "baroque-oil-painting": {
        "name": "Historical Epic / Baroque Oil Painting",
        "image_prompt_prefix": (
            "Baroque oil painting style, dramatic chiaroscuro lighting, museum-quality historical scene, "
            "rich earth tones with gold and crimson accents, painterly brushwork texture visible, dramatic "
            "sky with volumetric clouds, historical period-accurate costuming, cinematic heroic composition, 16:9."
        ),
        "style_brief": (
            "Render as a Baroque oil painting — museum quality, not a digital imitation. Chiaroscuro is "
            "essential: a powerful key light against deep shadow defines every element. The palette uses "
            "rich earth tones (ochre, burnt sienna, raw umber) with gold, deep crimson, and occasional cobalt "
            "as accents. Brushwork texture should be visible. Historical period must be visually accurate in "
            "costume, architecture, and weapons. Composition should follow Baroque dramatic diagonals — no "
            "static symmetry. Sky, if included, should have volumetric storm clouds with light breaking through. "
            "Subjects should look heroic, tragic, or both. Treat each image as a major historical painting."
        ),
    },
    "golden-hour-motivational": {
        "name": "Motivational Golden Hour",
        "image_prompt_prefix": (
            "Epic landscape at golden hour, lone silhouette figure on elevated terrain, dramatic volumetric "
            "god rays breaking through storm clouds, warm orange and gold color palette, cinematic wide-angle "
            "composition, majestic scale, inspirational triumph atmosphere, 16:9."
        ),
        "style_brief": (
            "Render as a motivational / stoicism YouTube thumbnail. The hero element is always a lone "
            "silhouette figure on elevated terrain — mountain summit, desert ridge, cliff edge, ruined tower. "
            "Golden hour sun breaks through dramatic storm clouds with volumetric god rays. The entire palette "
            "is warm: deep oranges, burnished golds, amber. The scale must make the human figure feel "
            "simultaneously small against nature and triumphant in having reached this point. The mood is: "
            "I did the hard thing. Cinematic wide-angle composition. This image must make the viewer feel "
            "motivated. No text elements within the image — leave clear space for title overlay."
        ),
    },
    "space-cosmic": {
        "name": "Space & Cosmic Wonder",
        "image_prompt_prefix": (
            "Photorealistic space scene, Hubble Space Telescope aesthetic, vast nebula with swirling deep "
            "purple and electric blue gas clouds, embedded star clusters, dramatic scale contrast, NASA-quality "
            "composition, cinematic depth of field, awe-inspiring cosmic atmosphere, 16:9."
        ),
        "style_brief": (
            "Render as a NASA/Hubble-quality space visualization. The dominant element is a vast nebula: "
            "swirling gas clouds in deep purple, violet, electric blue, and magenta with embedded star clusters "
            "glowing at their cores. Scale must communicate cosmic awe — a planet or spacecraft in the corner "
            "provides scale reference. The background is absolute black with dense star fields. High contrast "
            "between the glowing nebula and dark space. Color palette: deep purple, electric blue, teal, with "
            "bright white stellar cores. The mood is pure wonder at the scale of the universe. Photorealistic "
            "render quality — this should look like it could be a real astronomical photograph."
        ),
    },
    "post-apocalyptic": {
        "name": "Post-Apocalyptic / Dystopian",
        "image_prompt_prefix": (
            "Post-apocalyptic urban ruin, collapsed skyscrapers overgrown with vegetation, amber dust haze sky, "
            "muted desaturated color palette, lone survivor silhouette in distance, ominous overcast atmosphere, "
            "photorealistic concept art quality, wide establishing shot, 16:9."
        ),
        "style_brief": (
            "Render as post-apocalyptic concept art. The setting is a major city 50+ years after collapse: "
            "skyscrapers broken and crumbling, streets overtaken by weeds and small trees, vehicles rusted and "
            "abandoned. An amber or sepia dust haze fills the atmosphere, desaturating all colors slightly. The "
            "palette is muted: weathered concrete grays, rust oranges, muted greens of encroaching vegetation, "
            "amber sky. A lone small human silhouette in the mid-distance establishes scale and desolation. No "
            "living crowds — emptiness is essential. Photorealistic concept art quality similar to The Last of "
            "Us or Fallout environmental art."
        ),
    },
    "flat-vector-educational": {
        "name": "Kurzgesagt Flat Vector",
        "image_prompt_prefix": (
            "Flat vector illustration in Kurzgesagt style, bold geometric shapes, clean solid color fills, "
            "expressive bird-like or simplified human characters with round eyes, bright saturated palette on "
            "deep blue or dark background, educational infographic composition, no shadows except stylized, "
            "clean professional 2D, 16:9."
        ),
        "style_brief": (
            "Render in the Kurzgesagt YouTube visual style — the gold standard of flat vector educational "
            "illustration. Every element is built from clean geometric shapes with bold solid color fills. No "
            "photorealism, no gradients within shapes except deliberate stylized ones. Characters are simplified "
            "and charming: bird-like figures with large round eyes and expressive tiny limbs, or geometric "
            "simplified humans. The palette is bold and saturated: deep navy or dark backgrounds with vibrant "
            "foreground elements in warm oranges, yellows, teals, and pinks. Stylized shadows use a darker version "
            "of the base color. The composition should feel like it explains a complex topic through visual clarity "
            "— every element serves the educational message."
        ),
    },
    "anime-shonen-action": {
        "name": "Anime Action / Shonen",
        "image_prompt_prefix": (
            "High-quality anime key visual, shonen action style, dynamic dramatic pose, vibrant saturated colors, "
            "bold ink outlines, cel-shading with strong specular highlights, speed lines background, cinematic rim "
            "lighting, expressive character with large detailed eyes, manga panel energy, 16:9."
        ),
        "style_brief": (
            "Render as a premium anime key visual in shonen action style. Character design follows anime proportion "
            "conventions: large expressive eyes, detailed hair, slightly exaggerated anatomy. Cel-shading with strong "
            "specular highlights and colored rim lights (often blue or orange). Palette is vibrant and saturated — high "
            "contrast between character and background. Speed lines or environmental particle effects suggest motion and "
            "power. The composition should feel like a stopped moment of peak dramatic intensity — the frame before "
            "everything changes. Background can be abstract with speed lines or a simplified dramatic environment. "
            "Professional anime studio quality — think Demon Slayer or Jujutsu Kaisen key art."
        ),
    },
    "cyberpunk-neon": {
        "name": "Cyberpunk / Neo-Noir",
        "image_prompt_prefix": (
            "Cyberpunk cityscape, rain-soaked neon-lit streets at night, teal and magenta neon reflections on wet "
            "pavement, Blade Runner atmosphere, holographic advertisements, moody noir lighting, chrome and glass "
            "architecture, cinematic fog, ultra-detailed concept art, 16:9."
        ),
        "style_brief": (
            "Render in cyberpunk neo-noir style. The setting is always a rain-soaked nocturnal city with neon signs "
            "in teal/cyan and magenta/pink reflecting on every wet surface. Architecture is dense: towering glass and "
            "chrome buildings stacked with neon advertisements. Atmospheric fog at street level. The palette is: "
            "near-black background with teal, magenta, and electric blue as the only light sources. Characters, if "
            "present, have cybernetic details visible. The mood references Blade Runner, Ghost in the Shell, and Akira "
            "— densely detailed, moody, and technically beautiful. Every frame should feel like a movie still from a "
            "$200M cyberpunk film."
        ),
    },
    "synthwave-retrowave": {
        "name": "Synthwave / Retrowave",
        "image_prompt_prefix": (
            "Retrowave 80s aesthetic, neon pink and electric cyan color palette, retro perspective grid receding to "
            "horizon, palm tree silhouettes against sunset gradient sky, chrome lettering, VHS grain texture and "
            "scanlines, Outrun style, deep purple-black background, glowing neon outline shapes, 16:9."
        ),
        "style_brief": (
            "Render in synthwave / retrowave style. The defining elements: a deep purple-black sky with a hot pink/"
            "magenta gradient horizon, a glowing neon grid receding in perspective to a vanishing point, and palm tree "
            "silhouettes. Neon colors are restricted to hot pink, electric cyan, and occasionally electric purple — no "
            "other hues. VHS artifacts are subtle but present: faint scanlines, slight color aberration at edges, mild "
            "grain. Chrome or neon-outlined 80s geometric shapes (triangles, mountains, sun) complete the composition. "
            "The aesthetic references Outrun game art, Miami Vice, and synthwave album covers. The mood is: nostalgic "
            "future, the 1980s imagined from 1985."
        ),
    },
    "psychological-surrealism": {
        "name": "Psychological Surrealism",
        "image_prompt_prefix": (
            "Salvador Dali-inspired surrealist scene, impossible architecture defying physics, reality distortion with "
            "symbolic objects, consciousness fracturing visual metaphor, muted beige and taupe palette with one vivid "
            "symbolic accent color, introspective dread, cinematic impossible composition, 16:9."
        ),
        "style_brief": (
            "Render in psychological surrealism style inspired by Salvador Dali and René Magritte. The scene violates "
            "physics in a deliberate, symbolic way: staircases lead to nowhere, rooms float in void, figures multiply, "
            "clocks melt, eyes appear where they shouldn't. Every element is a symbol that represents a psychological "
            "concept — anxiety, identity, memory, consciousness. The palette is restrained: muted beige, taupe, pale "
            "gray dominate, with one single vivid accent color (electric red, deep blue, bright yellow) that draws the "
            "eye to the symbolic focal point. The mood should provoke introspection rather than fear. The viewer should "
            "feel: 'this is impossible but I understand it.' Painterly quality, not digital-slick."
        ),
    },
}


def resolve_style(style_id: str) -> StyleResult:
    """Resolve any style_id to a StyleResult.

    Args:
        style_id: namespaced string — "dna:UCxxxxx", "preset:anime",
                  or "custom:<uuid4>".

    Returns:
        StyleResult with all fields populated (some may be empty strings/lists
        if the style type doesn't support that dimension).

    Raises:
        ValueError: if style_id is malformed or the referenced style doesn't exist.
        RuntimeError: if a DNA channel can't be resolved.
    """
    if not style_id or ":" not in style_id:
        raise ValueError(f"Invalid style_id {style_id!r} — expected 'type:value'")

    prefix, _, value = style_id.partition(":")

    if prefix == "dna":
        return _resolve_dna(value)
    elif prefix == "preset":
        return _resolve_preset(value)
    elif prefix == "custom":
        return _resolve_custom(value)
    else:
        raise ValueError(f"Unknown style type {prefix!r} in style_id {style_id!r}")


def _resolve_dna(channel_id: str) -> StyleResult:
    """Resolve a YouTube channel's DNA (existing behavior)."""
    from core.style_channel import resolve_style_channel

    sc = resolve_style_channel(channel_id)
    if not sc:
        raise RuntimeError(f"Could not resolve DNA channel '{channel_id}'")

    return StyleResult(
        style_brief=sc.get("style_brief") or "",
        reference_images=list(sc.get("all_reference_paths") or sc.get("reference_paths") or []),
        image_prompt_prefix="",  # DNA uses reference images + brief, no prefix
        text_dna=sc.get("text_dna") or "",
        label=sc.get("handle") or sc.get("name") or channel_id,
    )


def _resolve_preset(slug: str) -> StyleResult:
    """Resolve a hardcoded preset style."""
    p = PRESETS.get(slug)
    if not p:
        raise ValueError(f"Unknown preset style {slug!r}. Valid slugs: {list(PRESETS)}")

    return StyleResult(
        style_brief=p["style_brief"],
        reference_images=[],      # presets have no reference images
        image_prompt_prefix=p["image_prompt_prefix"],
        text_dna="",
        label=p["name"],
    )


def _resolve_custom(uuid4: str) -> StyleResult:
    """Resolve a custom user-uploaded style from the database."""
    from data.db import db

    d = db()
    style_id = f"custom:{uuid4}"

    if "styles" not in d.table_names():
        raise ValueError(f"Custom style '{style_id}' not found (no styles table)")

    try:
        row = d["styles"].get(style_id)
    except Exception:
        row = None

    if not row:
        raise ValueError(f"Custom style '{style_id}' not found")

    raw_paths: list[str] = json.loads(row.get("image_paths") or "[]")
    ref_images = [Path(p) for p in raw_paths if Path(p).exists()]

    return StyleResult(
        style_brief=row.get("style_brief") or row.get("description") or "",
        reference_images=ref_images,
        image_prompt_prefix=row.get("image_prompt_prefix") or "",
        text_dna="",
        label=row.get("name") or uuid4,
    )


def list_all_styles() -> list[dict[str, Any]]:
    """Return all available styles in a unified list for the picker API.

    Each item has: {id, style_type, name, (optional) channel_id, handle, subs, thumbnail_url}
    """
    out: list[dict[str, Any]] = []

    # DNA styles — from tracked channels
    try:
        from core.style_channel import list_style_channels

        for ch in list_style_channels():
            out.append({
                "id": f"dna:{ch['channel_id']}",
                "style_type": "dna",
                "name": f"@{ch['handle'] or ch['name']}",
                "channel_id": ch["channel_id"],
                "handle": ch.get("handle", ""),
                "subs": ch.get("subs", 0),
                "thumbnail_url": None,
            })
    except Exception:
        pass

    # Preset styles
    for slug, p in PRESETS.items():
        out.append({
            "id": f"preset:{slug}",
            "style_type": "preset",
            "name": p["name"],
            "thumbnail_url": None,
        })

    # Custom styles
    try:
        from data.db import db

        d = db()
        if "styles" in d.table_names():
            for row in d["styles"].rows_where(order_by="created_at desc"):
                raw_paths: list[str] = json.loads(row.get("image_paths") or "[]")
                first_img = next((p for p in raw_paths if Path(p).exists()), None)
                uuid_part = row["id"].split(":", 1)[1] if ":" in row["id"] else row["id"]
                out.append({
                    "id": row["id"],
                    "style_type": "custom",
                    "name": row["name"],
                    "description": row.get("description", ""),
                    "thumbnail_url": f"/custom-styles/{uuid_part}/ref_0.jpg" if first_img else None,
                })
    except Exception:
        pass

    return out
