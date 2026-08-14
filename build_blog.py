#!/usr/bin/env python3
"""Build posts/*.md -> posts/*.html, regenerate blog.html index."""
import re
from pathlib import Path

import markdown

from site_shared import render_site_header

ROOT = Path(__file__).parent
POSTS_DIR = ROOT / "posts"
FILENAME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-(.+)\.md$")

METERS = '    <a href="/status.html" class="meters-link"><div class="meters" id="meters"></div></a>'
SITE_HEADER = render_site_header("blog")

POST_TEMPLATE = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{{title}} — Mihai Cosma</title>
    <link rel="stylesheet" href="/style.css">
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


def parse_post(path: Path):
    m = FILENAME_RE.match(path.name)
    if not m:
        raise ValueError(f"bad filename (need YYYY-MM-DD-slug.md): {path.name}")
    date_str, slug = m.group(1), m.group(2)
    text = path.read_text()
    title_match = re.match(r"#\s+(.+)", text)
    if not title_match:
        raise ValueError(f"{path.name}: first line must be '# Title'")
    title = title_match.group(1).strip()
    body_md = text[title_match.end():].lstrip("\n")
    body_html = markdown.markdown(body_md, extensions=["fenced_code", "tables"])
    return date_str, slug, title, body_html


def main():
    POSTS_DIR.mkdir(exist_ok=True)
    posts = []
    for path in sorted(POSTS_DIR.glob("*.md")):
        date_str, slug, title, body = parse_post(path)
        html = POST_TEMPLATE.format(title=title, date_str=date_str, body=body)
        (POSTS_DIR / f"{slug}.html").write_text(html)
        posts.append((date_str, slug, title))

    posts.sort(reverse=True)
    items = "\n".join(
        f'        <li><span class="post-list-date">{d}</span><a href="/posts/{s}.html">{t}</a></li>'
        for d, s, t in posts
    ) or '        <li class="post-list-empty">no posts yet</li>'
    (ROOT / "blog.html").write_text(INDEX_TEMPLATE.format(items=items))
    print(f"built {len(posts)} post(s)")


if __name__ == "__main__":
    main()
