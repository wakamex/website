"""Render a blog post's link-preview card in the site style, laid out like a repository preview card."""

import io
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 1200, 630
FONT = Path(__file__).with_name("ClankerMono-NF.ttf")
# Colours from the site style (/code/styles/based.md): near-black ground, light grey primary text,
# warm muted secondary text, and orange as the single accent.
BACKGROUND = (4, 5, 6)
PRIMARY = (224, 224, 224)
SECONDARY = (182, 170, 153)
ACCENT = (255, 152, 0)
MARGIN = 72
COLUMN = WIDTH - 2 * MARGIN
# Phones show cards about 500px wide, so text is at least 30px to stay legible after scaling.
LABEL_SIZE = 30
TITLE_SIZES = (68, 60, 52)  # largest first, until the title fits in three lines
SUBTITLE_SIZE = 38
STRIP = 10


def wrap(text, font, width):
    lines = []
    for word in text.split():
        candidate = f"{lines[-1]} {word}" if lines else word
        if lines and font.getlength(candidate) <= width:
            lines[-1] = candidate
        else:
            lines.append(word)
    return lines


def balanced_wrap(text, font, width):
    """Wrap into as few lines as fit, then narrow the measure so the lines come out even."""
    lines = wrap(text, font, width)
    while width > 0 and len(wrap(text, font, width - 8)) == len(lines):
        width -= 8
        lines = wrap(text, font, width)
    return lines


def font(size):
    return ImageFont.truetype(str(FONT), size)


def render_card(title, subtitle=None, meta=None):
    """Return the card as PNG bytes: site label, title, optional subtitle, and an optional meta line at the foot."""
    card = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND)
    draw = ImageDraw.Draw(card)
    label_font = font(LABEL_SIZE)

    draw.text((MARGIN, MARGIN), "Mihai Cosma / Blog", font=label_font, fill=SECONDARY)

    for size in TITLE_SIZES:
        title_font = font(size)
        title_lines = balanced_wrap(title, title_font, COLUMN)
        if len(title_lines) <= 3:
            break
    y = MARGIN + 88
    for line in title_lines:
        draw.text((MARGIN, y), line, font=title_font, fill=PRIMARY)
        y += round(title_font.size * 1.18)

    if subtitle:
        subtitle_font = font(SUBTITLE_SIZE)
        y += 18
        for line in balanced_wrap(subtitle, subtitle_font, COLUMN)[:2]:
            draw.text((MARGIN, y), line, font=subtitle_font, fill=SECONDARY)
            y += round(SUBTITLE_SIZE * 1.35)

    if meta:
        draw.text((MARGIN, HEIGHT - STRIP - MARGIN + 10 - LABEL_SIZE), meta, font=label_font, fill=SECONDARY)
    draw.rectangle((0, HEIGHT - STRIP, WIDTH, HEIGHT), fill=ACCENT)

    output = io.BytesIO()
    card.save(output, format="PNG", optimize=True)
    return output.getvalue()
