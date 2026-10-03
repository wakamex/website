"""Render a blog post's link-preview card: one site style for every post."""

import io
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 1200, 630
FONT = Path(__file__).with_name("ClankerMono-NF.ttf")
BACKGROUND = (4, 5, 6)
TITLE_COLOUR = (224, 224, 224)
SUBTITLE_COLOUR = (255, 152, 0)
LEFT = 72
COLUMN = 800
GAP = 30
# A short orange bar above the title, like the underline on the site's active menu tab.
RULE = (72, 6)
RULE_GAP = 34
# Title sizes to try, largest first, until the title fits in three lines.
TITLE_SIZES = (64, 56, 48)
SUBTITLE_SIZE = 40
# Phones show cards about 500px wide, so nothing smaller than 40px stays legible; keep the subtitle to two lines.
SUBTITLE_LINES = 2


def wrap(text, font, width):
    lines = []
    for word in text.split():
        candidate = f"{lines[-1]} {word}" if lines else word
        if lines and font.getlength(candidate) <= width:
            lines[-1] = candidate
        else:
            lines.append(word)
    return lines


def cover(data):
    """Scale and centre-crop a background image to fill the card."""
    image = Image.open(io.BytesIO(data)).convert("RGB")
    scale = max(WIDTH / image.width, HEIGHT / image.height)
    image = image.resize((round(image.width * scale), round(image.height * scale)), Image.LANCZOS)
    left, top = (image.width - WIDTH) // 2, (image.height - HEIGHT) // 2
    return image.crop((left, top, left + WIDTH, top + HEIGHT))


def fade():
    """Dark behind the text column, clearing towards the right so a background shows there."""
    stops = [(0.0, 0.94), (0.62, 0.9), (0.86, 0.4), (1.0, 0.12)]
    alpha = Image.new("L", (WIDTH, 1))
    for x in range(WIDTH):
        t = x / (WIDTH - 1)
        for (t0, a0), (t1, a1) in zip(stops, stops[1:]):
            if t0 <= t <= t1:
                alpha.putpixel((x, 0), round(255 * (a0 + (a1 - a0) * (t - t0) / (t1 - t0))))
                break
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (*BACKGROUND, 0))
    overlay.putalpha(alpha.resize((WIDTH, HEIGHT)))
    return overlay


def render_card(title, subtitle=None, background=None):
    """Return the card as PNG bytes. background is optional image bytes shown behind the fade."""
    card = cover(background).convert("RGBA") if background else Image.new("RGBA", (WIDTH, HEIGHT), (*BACKGROUND, 255))
    if background:
        card = Image.alpha_composite(card, fade())
    draw = ImageDraw.Draw(card)

    for size in TITLE_SIZES:
        title_font = ImageFont.truetype(str(FONT), size)
        title_lines = wrap(title, title_font, COLUMN)
        if len(title_lines) <= 3:
            break
    subtitle_font = ImageFont.truetype(str(FONT), SUBTITLE_SIZE)
    subtitle_lines = wrap(subtitle, subtitle_font, COLUMN)[:SUBTITLE_LINES] if subtitle else []

    title_step = round(title_font.size * 1.15)
    subtitle_step = round(SUBTITLE_SIZE * 1.3)
    height = RULE[1] + RULE_GAP + len(title_lines) * title_step + (GAP + len(subtitle_lines) * subtitle_step if subtitle_lines else 0)
    y = (HEIGHT - height) // 2
    draw.rectangle((LEFT, y, LEFT + RULE[0] - 1, y + RULE[1] - 1), fill=SUBTITLE_COLOUR)
    y += RULE[1] + RULE_GAP
    for line in title_lines:
        draw.text((LEFT, y), line, font=title_font, fill=TITLE_COLOUR)
        y += title_step
    y += GAP
    for line in subtitle_lines:
        draw.text((LEFT, y), line, font=subtitle_font, fill=SUBTITLE_COLOUR)
        y += subtitle_step

    output = io.BytesIO()
    card.convert("RGB").save(output, format="PNG", optimize=True)
    return output.getvalue()
