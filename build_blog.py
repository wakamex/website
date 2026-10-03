#!/usr/bin/env python3
"""Build blog/*.md -> blog/*.html and regenerate the blog index."""
import html
import re
import struct
import subprocess
from pathlib import Path

import markdown

from site_shared import render_site_header, write_if_changed

ROOT = Path(__file__).parent
BLOG_REPO = Path("/code/blog")
BLOG_OUTPUT_DIR = ROOT / "blog"
FILENAME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-(.+)\.md$")
SITE_URL = "https://mihaicosma.com"
SITE_IMAGE = (f"{SITE_URL}/og-image.png", 1200, 630)
DESCRIPTION_LIMIT = 200
ASCIINEMA_SHORTCODE_RE = re.compile(
    r'^[ \t]*\{\{\s*asciinema\("([^"\r\n]+)"\)\s*\}\}[ \t]*$', re.MULTILINE
)
ASCIINEMA_PLAYER_VERSION = "3.17.0"

ASCIINEMA_HEAD = (
    f'    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/asciinema-player@'
    f'{ASCIINEMA_PLAYER_VERSION}/dist/bundle/asciinema-player.css">'
)
ASCIINEMA_SCRIPTS = f"""    <script src="https://cdn.jsdelivr.net/npm/asciinema-player@{ASCIINEMA_PLAYER_VERSION}/dist/bundle/asciinema-player.min.js"></script>
    <script>
        document.querySelectorAll("[data-asciinema]").forEach(function (element) {{
            AsciinemaPlayer.create(element.dataset.asciinema, element, {{
                idleTimeLimit: 2,
                poster: "npt:0:01",
                preload: true
            }});
        }});
    </script>"""

METERS = '    <a href="/status.html" class="meters-link"><div class="meters" id="meters"></div></a>'
SITE_HEADER = render_site_header("blog")

POST_TEMPLATE = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{{title}} — Mihai Cosma</title>
    <link rel="canonical" href="https://mihaicosma.com/blog/{{slug}}.html">
    <link rel="stylesheet" href="/style.css">
{{social_head}}
{{extra_head}}
</head>
<body>
{SITE_HEADER}
{METERS}
    <article class="post">
        <h1>{{title}}</h1>
        <p class="post-meta">{{date_str}}</p>
{{body}}
    </article>
    <script src="/meters.js"></script>
    <script src="/site-nav.js"></script>
{{extra_scripts}}
</body>
</html>
"""

INDEX_TEMPLATE = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Blog — Mihai Cosma</title>
    <link rel="stylesheet" href="/style.css">
</head>
<body>
{SITE_HEADER}
{METERS}
    <h1>Blog</h1>
    <ul class="post-list">
{{items}}
    </ul>
    <script src="/meters.js"></script>
    <script src="/site-nav.js"></script>
</body>
</html>
"""

LEGACY_REDIRECT = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Blog - Mihai Cosma</title>
    <link rel="canonical" href="/blog/">
    <meta http-equiv="refresh" content="0; url=/blog/">
</head>
<body>
    <p><a href="/blog/">Continue to the blog</a></p>
</body>
</html>
"""


def describe(body_html):
    """The first paragraph as plain text, cut at a word near DESCRIPTION_LIMIT characters."""
    match = re.search(r"<p>(.*?)</p>", body_html, re.DOTALL)
    text = " ".join(html.unescape(re.sub(r"<[^>]+>", "", match.group(1))).split()) if match else ""
    if len(text) > DESCRIPTION_LIMIT:
        text = text[:DESCRIPTION_LIMIT].rsplit(" ", 1)[0].rstrip(",;:") + "..."
    return text


def png_size(data: bytes):
    if data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        raise ValueError("not a PNG")
    return struct.unpack(">II", data[16:24])


def render_social_head(slug, title, body, image=None):
    """Open Graph and Twitter card tags, so shared links show a preview. image is (url, width, height)."""
    url, width, height = image or SITE_IMAGE
    tags = [
        ("property", "og:type", "article"),
        ("property", "og:title", title),
        ("property", "og:description", describe(body)),
        ("property", "og:url", f"{SITE_URL}/blog/{slug}.html"),
        ("property", "og:image", url),
        ("property", "og:image:width", str(width)),
        ("property", "og:image:height", str(height)),
        ("name", "twitter:card", "summary_large_image"),
    ]
    return "\n".join(
        f'    <meta {kind}="{key}" content="{html.escape(value, quote=True)}">'
        for kind, key, value in tags
    )


def parse_post_text(filename: str, text: str):
    m = FILENAME_RE.match(filename)
    if not m:
        raise ValueError(f"bad filename (need YYYY-MM-DD-slug.md): {filename}")
    date_str, slug = m.group(1), m.group(2)
    title_match = re.match(r"#\s+(.+)", text)
    if not title_match:
        raise ValueError(f"{filename}: first line must be '# Title'")
    title = title_match.group(1).strip()
    body_md = text[title_match.end():].lstrip("\n")
    body_md = ASCIINEMA_SHORTCODE_RE.sub(
        lambda match: f'<div data-asciinema="{html.escape(match.group(1), quote=True)}"></div>',
        body_md,
    )
    if re.search(r"\{\{\s*asciinema\b", body_md):
        raise ValueError(
            f'{filename}: invalid asciinema shortcode; use '
            f'{{{{ asciinema("/demo.cast") }}}}'
        )
    body_html = markdown.markdown(
        body_md,
        extensions=["fenced_code", "tables", "toc"],
        extension_configs={"toc": {"separator": "_"}},
    )
    return date_str, slug, title, body_html


def parse_post(path: Path):
    return parse_post_text(path.name, path.read_text())


def committed_names(repo: Path):
    return subprocess.check_output(
        [
            "git",
            "-C",
            str(repo),
            "ls-tree",
            "-r",
            "-z",
            "--name-only",
            "HEAD",
        ]
    ).decode().split("\0")


def committed_markdown(repo: Path):
    for name in sorted(name for name in committed_names(repo) if name.endswith(".md")):
        text = subprocess.check_output(
            ["git", "-C", str(repo), "show", f"HEAD:{name}"], text=True
        )
        yield name, text


def render_post(date_str, slug, title, body, image=None):
    has_asciinema = "data-asciinema=" in body
    return POST_TEMPLATE.format(
        title=title,
        slug=slug,
        social_head=render_social_head(slug, title, body, image),
        date_str=date_str,
        body=body,
        extra_head=ASCIINEMA_HEAD if has_asciinema else "",
        extra_scripts=ASCIINEMA_SCRIPTS if has_asciinema else "",
    )


def main():
    BLOG_OUTPUT_DIR.mkdir(exist_ok=True)
    expected_outputs = set()
    files_written = 0
    posts = []
    skipped = []
    names = set(committed_names(BLOG_REPO))
    for filename, text in committed_markdown(BLOG_REPO):
        # Posts are top-level YYYY-MM-DD-slug.md files; other Markdown, such as AGENTS.md, is repository documentation.
        if not FILENAME_RE.match(filename):
            skipped.append(filename)
            continue
        date_str, slug, title, body = parse_post_text(filename, text)
        # A post's preview image is a committed PNG with the post's own name, such as 2026-10-02-slug.png.
        image = None
        image_name = filename[:-3] + ".png"
        if image_name in names:
            data = subprocess.check_output(["git", "-C", str(BLOG_REPO), "show", f"HEAD:{image_name}"])
            image_output = BLOG_OUTPUT_DIR / f"{slug}.png"
            if not image_output.exists() or image_output.read_bytes() != data:
                image_output.write_bytes(data)
                files_written += 1
            expected_outputs.add(image_output)
            image = (f"{SITE_URL}/blog/{slug}.png", *png_size(data))
        rendered = render_post(date_str, slug, title, body, image)
        output = BLOG_OUTPUT_DIR / f"{slug}.html"
        files_written += write_if_changed(output, rendered)
        expected_outputs.add(output)
        posts.append((date_str, slug, title))

    posts.sort(reverse=True)
    items = "\n".join(
        f'        <li><span class="post-list-date">{d}</span><a href="/blog/{s}.html">{t}</a></li>'
        for d, s, t in posts
    ) or '        <li class="post-list-empty">no posts yet</li>'
    index_output = BLOG_OUTPUT_DIR / "index.html"
    files_written += write_if_changed(index_output, INDEX_TEMPLATE.format(items=items))
    expected_outputs.add(index_output)
    for path in [*BLOG_OUTPUT_DIR.glob("*.html"), *BLOG_OUTPUT_DIR.glob("*.png")]:
        if path not in expected_outputs:
            path.unlink()
    files_written += write_if_changed(ROOT / "blog.html", LEGACY_REDIRECT)
    summary = f"checked {len(posts)} post(s), wrote {files_written} file(s)"
    if skipped:
        summary += f"; skipped non-post Markdown: {', '.join(skipped)}"
    print(summary)


if __name__ == "__main__":
    main()
