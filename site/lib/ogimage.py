"""Generates 1200x630 Open Graph images at build time (BRIEF.md section 10).
Uses a build-time-only TTF (site/build_assets/Manrope-Variable.ttf) — never shipped to dist/,
the site itself only ever serves the self-hosted woff2 files."""
from __future__ import annotations

import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONT_PATH = Path(__file__).resolve().parent.parent / "build_assets" / "Manrope-Variable.ttf"

PRIMARY_DARK = (18, 21, 27)
PRIMARY = (39, 44, 61)
BRAND_LABEL = (91, 141, 239)
WHITE = (255, 255, 255)
MUTED = (163, 170, 184)
GRADIENT_STOPS = [(239, 68, 68), (234, 163, 0), (34, 197, 94), (59, 130, 246)]

_font_cache: dict[tuple[int, int], ImageFont.FreeTypeFont] = {}


def _get_font(size: int, weight: int = 700) -> ImageFont.FreeTypeFont:
    key = (size, weight)
    if key not in _font_cache:
        font = ImageFont.truetype(str(FONT_PATH), size)
        try:
            font.set_variation_by_axes([weight])
        except Exception:
            pass
        _font_cache[key] = font
    return _font_cache[key]


def generate_og_image(title: str, subtitle: str, out_path: Path, brand: str = "") -> None:
    width, height = 1200, 630
    img = Image.new("RGB", (width, height), PRIMARY_DARK)
    draw = ImageDraw.Draw(img)

    for x in range(width):
        t = x / width
        r = int(PRIMARY_DARK[0] + (PRIMARY[0] - PRIMARY_DARK[0]) * t)
        g = int(PRIMARY_DARK[1] + (PRIMARY[1] - PRIMARY_DARK[1]) * t)
        b = int(PRIMARY_DARK[2] + (PRIMARY[2] - PRIMARY_DARK[2]) * t)
        draw.line([(x, 0), (x, height)], fill=(r, g, b))

    # 4-stop brand gradient bar (red -> yellow -> green -> blue) — the same
    # signature strip used as the footer's top border on the live site.
    bar_top = height - 14
    stops = GRADIENT_STOPS
    n = len(stops) - 1
    for x in range(width):
        t = x / width * n
        i = min(int(t), n - 1)
        local_t = t - i
        r = int(stops[i][0] + (stops[i + 1][0] - stops[i][0]) * local_t)
        g = int(stops[i][1] + (stops[i + 1][1] - stops[i][1]) * local_t)
        b = int(stops[i][2] + (stops[i + 1][2] - stops[i][2]) * local_t)
        draw.line([(x, bar_top), (x, height)], fill=(r, g, b))

    margin = 80
    if brand:
        brand_font = _get_font(26, 700)
        draw.text((margin, 64), brand.upper(), font=brand_font, fill=BRAND_LABEL)

    title_font = _get_font(58, 800)
    wrapped = textwrap.wrap(title, width=20)[:3]
    y = 190
    for line in wrapped:
        draw.text((margin, y), line, font=title_font, fill=WHITE)
        y += 70

    if subtitle:
        subtitle_font = _get_font(28, 500)
        sub_wrapped = textwrap.wrap(subtitle, width=48)[:2]
        y += 18
        for line in sub_wrapped:
            draw.text((margin, y), line, font=subtitle_font, fill=MUTED)
            y += 40

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "PNG", optimize=True)


def generate_placeholder_svg(out_path: Path, width: int, height: int, label: str) -> None:
    """Simple labeled placeholder (per BRIEF.md section 4 — no stock photography)."""
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect width="{width}" height="{height}" fill="#eef1f6"/>
  <rect x="1" y="1" width="{width - 2}" height="{height - 2}" fill="none" stroke="#2563eb" stroke-width="2" stroke-dasharray="10 8"/>
  <text x="50%" y="48%" text-anchor="middle" font-family="sans-serif" font-size="{max(14, width // 28)}" fill="#1d4ed8" font-weight="700">{label}</text>
  <text x="50%" y="58%" text-anchor="middle" font-family="sans-serif" font-size="{max(11, width // 40)}" fill="#5c6472">{width}×{height} — заменить на реальное фото</text>
</svg>
'''
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(svg, encoding="utf-8")
