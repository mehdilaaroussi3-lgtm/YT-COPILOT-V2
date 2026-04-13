"""Post-processing effects: grain, vignette, simple color grading."""
from __future__ import annotations

import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter


def add_grain(img: Image.Image, intensity: float = 0.15) -> Image.Image:
    """Apply film-style noise."""
    if intensity <= 0:
        return img
    noise = Image.effect_noise(img.size, sigma=int(60 * intensity)).convert("L")
    grain_layer = Image.merge("RGBA", (noise, noise, noise,
                                       noise.point(lambda p: int(p * intensity * 0.6))))
    return Image.alpha_composite(img.convert("RGBA"), grain_layer).convert("RGB")


def add_vignette(img: Image.Image, strength: float = 0.6) -> Image.Image:
    """Darken corners radially."""
    w, h = img.size
    mask = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(mask)
    # White ellipse, then blur. White stays bright, black corners darken.
    pad_x, pad_y = int(w * 0.1), int(h * 0.1)
    draw.ellipse([-pad_x, -pad_y, w + pad_x, h + pad_y], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(radius=min(w, h) * 0.15))
    dark = Image.new("RGB", img.size, (0, 0, 0))
    return Image.composite(img, dark, mask.point(lambda p: int(p * (1 - strength) + p * strength)))


def color_grade(img: Image.Image, preset: str) -> Image.Image:
    """Quick LUT-style grade. Presets: cyberpunk, cinematic, noir, editorial, natural."""
    if preset == "noir":
        img = ImageEnhance.Color(img).enhance(0.3)
        img = ImageEnhance.Contrast(img).enhance(1.25)
    elif preset == "cyberpunk":
        img = ImageEnhance.Color(img).enhance(1.35)
        img = ImageEnhance.Contrast(img).enhance(1.15)
    elif preset == "cinematic":
        img = ImageEnhance.Contrast(img).enhance(1.1)
        img = ImageEnhance.Color(img).enhance(0.9)
    elif preset == "editorial":
        img = ImageEnhance.Contrast(img).enhance(1.08)
    return img


def apply_post(image_path: Path, out_path: Path, *,
                grain: float = 0.0, vignette: bool = False,
                grade: str | None = None) -> Path:
    img = Image.open(image_path).convert("RGB")
    if grade:
        img = color_grade(img, grade)
    if vignette:
        img = add_vignette(img)
    if grain > 0:
        img = add_grain(img, grain)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, format="PNG", optimize=True)
    return out_path
