"""Pillow text overlay engine — high-contrast, mobile-readable."""
from __future__ import annotations

from pathlib import Path
from typing import Literal

from PIL import Image, ImageDraw, ImageFont

from compositing.safe_zone import validate_text_placement

FONT_DIR = Path(__file__).resolve().parent / "fonts"

FONTS = {
    "inter":  FONT_DIR / "Inter-Black.ttf",
    "anton":  FONT_DIR / "Anton-Regular.ttf",
    "oswald": FONT_DIR / "Oswald-Bold.ttf",
}

Position = Literal["upper", "center", "lower", "left", "right"]


def load_font(name: str, size: int) -> ImageFont.FreeTypeFont:
    path = FONTS.get(name.lower(), FONTS["inter"])
    return ImageFont.truetype(str(path), size)


def fit_font_size(text: str, image_w: int, font_name: str,
                   target_width_ratio: float = 0.7,
                   max_size: int = 220, min_size: int = 60) -> ImageFont.FreeTypeFont:
    """Pick the largest size where text width <= target_width_ratio of image_w."""
    target_w = image_w * target_width_ratio
    size = max_size
    while size > min_size:
        font = load_font(font_name, size)
        bbox = font.getbbox(text)
        if (bbox[2] - bbox[0]) <= target_w:
            return font
        size -= 6
    return load_font(font_name, min_size)


def position_for(position: Position, image_size: tuple[int, int],
                  text_size: tuple[int, int],
                  margin_ratio: float = 0.06) -> tuple[int, int]:
    iw, ih = image_size
    tw, th = text_size
    m = int(min(iw, ih) * margin_ratio)
    x = (iw - tw) // 2
    y = (ih - th) // 2
    if position == "upper":
        y = m
    elif position == "lower":
        y = ih - th - m - int(ih * 0.05)   # avoid progress bar
    elif position == "left":
        x = m
    elif position == "right":
        x = iw - tw - m
    return x, y


def overlay_text(
    image_path: Path,
    text: str,
    out_path: Path,
    *,
    font_name: str = "inter",
    position: Position = "upper",
    fill: str = "#FFFFFF",
    stroke_color: str = "#000000",
    stroke_width: int = 6,
    shadow: bool = True,
    target_width_ratio: float = 0.7,
) -> dict:
    """Render text on an image and save. Returns metadata + safe-zone report."""
    img = Image.open(image_path).convert("RGBA")
    iw, ih = img.size

    font = fit_font_size(text, iw, font_name, target_width_ratio=target_width_ratio)
    bbox = font.getbbox(text)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x, y = position_for(position, (iw, ih), (tw, th))

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    if shadow:
        for dx, dy, a in [(8, 8, 140), (4, 4, 90)]:
            draw.text((x + dx, y + dy), text, font=font,
                      fill=(0, 0, 0, a), stroke_width=stroke_width // 2,
                      stroke_fill=(0, 0, 0, a))
    draw.text((x, y), text, font=font, fill=fill,
              stroke_width=stroke_width, stroke_fill=stroke_color)

    composed = Image.alpha_composite(img, overlay).convert("RGB")

    text_bbox = (x, y, x + tw, y + th)
    safe = validate_text_placement(text_bbox, (iw, ih))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    composed.save(out_path, format="PNG", optimize=True)

    return {
        "out_path": str(out_path),
        "font": font_name,
        "font_size": font.size,
        "text_bbox": text_bbox,
        "safe": safe.safe,
        "warnings": safe.warnings,
    }
