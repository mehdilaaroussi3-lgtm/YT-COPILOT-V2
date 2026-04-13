"""YouTube homepage mockup generator (dark + light mode)."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from compositing.text_overlay import FONTS

# Mockup grid: 3 columns x 2 rows = 6 thumbs (yours + 5 placeholders)
COLS, ROWS = 3, 2
THUMB_W, THUMB_H = 400, 225      # 16:9
GAP = 24
PADDING_X, PADDING_Y_TOP = 32, 96
PADDING_Y_BOTTOM = 32

PLACEHOLDER_TITLES = [
    "Top 10 AI Tools You Need This Year",
    "Why Your Code Is Failing Faster",
    "Inside the $50B AI Race",
    "The Hidden Truth About Tech",
    "How Banks Are Lying to You",
]

PLACEHOLDER_CHANNELS = [
    "TechHub", "Code Daily", "Future Lab", "Money Brief", "AI Insider",
]


def _placeholder(idx: int, mode: str) -> Image.Image:
    """Solid-color block stand-in for competitor thumbnails."""
    palette_dark = [(35, 41, 70), (60, 28, 34), (28, 50, 38), (52, 48, 24), (45, 30, 60)]
    palette_light = [(220, 230, 245), (245, 220, 220), (220, 245, 230), (250, 240, 215), (235, 220, 250)]
    color = (palette_dark if mode == "dark" else palette_light)[idx % 5]
    img = Image.new("RGB", (THUMB_W, THUMB_H), color)
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(str(FONTS["inter"]), 32)
    label = f"#{idx + 1}"
    bbox = font.getbbox(label)
    tw = bbox[2] - bbox[0]; th = bbox[3] - bbox[1]
    text_color = (255, 255, 255, 60) if mode == "dark" else (0, 0, 0, 60)
    draw.text(((THUMB_W - tw) // 2, (THUMB_H - th) // 2), label,
              font=font, fill=text_color)
    return img


def _draw_meta(canvas: Image.Image, x: int, y: int, title: str, channel: str,
                mode: str) -> None:
    draw = ImageDraw.Draw(canvas)
    title_font = ImageFont.truetype(str(FONTS["inter"]), 18)
    chan_font = ImageFont.truetype(str(FONTS["inter"]), 14)
    fg = (255, 255, 255) if mode == "dark" else (15, 15, 15)
    sub = (170, 170, 170) if mode == "dark" else (100, 100, 100)
    # Truncate title
    if len(title) > 50:
        title = title[:47] + "..."
    draw.text((x, y), title, font=title_font, fill=fg)
    draw.text((x, y + 28), channel, font=chan_font, fill=sub)


def generate_mockup(thumbnail_path: Path, title: str, out_path: Path,
                     mode: str = "dark") -> Path:
    """Compose a YouTube-feed-style mockup with the given thumbnail in slot 0."""
    bg = (15, 15, 15) if mode == "dark" else (249, 249, 249)
    canvas_w = PADDING_X * 2 + COLS * THUMB_W + (COLS - 1) * GAP
    canvas_h = PADDING_Y_TOP + ROWS * (THUMB_H + 70) + (ROWS - 1) * GAP + PADDING_Y_BOTTOM
    canvas = Image.new("RGB", (canvas_w, canvas_h), bg)

    # Top bar
    draw = ImageDraw.Draw(canvas)
    bar_color = (33, 33, 33) if mode == "dark" else (255, 255, 255)
    draw.rectangle([0, 0, canvas_w, 56], fill=bar_color)
    title_font = ImageFont.truetype(str(FONTS["inter"]), 24)
    fg = (255, 255, 255) if mode == "dark" else (15, 15, 15)
    draw.text((PADDING_X, 16), "▶ YouTube", font=title_font, fill=(255, 0, 0))
    mode_label = "Dark Mode" if mode == "dark" else "Light Mode"
    draw.text((canvas_w - 200, 20), mode_label,
              font=ImageFont.truetype(str(FONTS["inter"]), 16), fill=fg)

    # Thumbnails grid
    user_thumb = Image.open(thumbnail_path).convert("RGB").resize((THUMB_W, THUMB_H))
    for i in range(COLS * ROWS):
        col = i % COLS
        row = i // COLS
        x = PADDING_X + col * (THUMB_W + GAP)
        y = PADDING_Y_TOP + row * (THUMB_H + GAP + 70)
        if i == 0:
            canvas.paste(user_thumb, (x, y))
            _draw_meta(canvas, x, y + THUMB_H + 8, title, "Your Channel", mode)
            # Highlight border
            draw.rectangle([x - 2, y - 2, x + THUMB_W + 2, y + THUMB_H + 2],
                           outline=(255, 215, 0), width=3)
        else:
            ph = _placeholder(i - 1, mode)
            canvas.paste(ph, (x, y))
            _draw_meta(canvas, x, y + THUMB_H + 8,
                       PLACEHOLDER_TITLES[(i - 1) % 5],
                       PLACEHOLDER_CHANNELS[(i - 1) % 5], mode)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_path, format="PNG", optimize=True)
    return out_path


def generate_mockup_pair(thumbnail_path: Path, title: str,
                          out_dir: Path) -> tuple[Path, Path]:
    dark = generate_mockup(thumbnail_path, title,
                           out_dir / "mockup_youtube_dark.png", "dark")
    light = generate_mockup(thumbnail_path, title,
                            out_dir / "mockup_youtube_light.png", "light")
    return dark, light
