#!/usr/bin/env python3
"""Validate and stage the public Inquisition prototype tree."""

from __future__ import annotations

import html
import re
import shutil
import sys
from pathlib import Path
from urllib.parse import quote

import markdown

from site_shared import render_site_header


SITE_HEADER = render_site_header(None)
METERS = '    <a href="/status.html" class="meters-link"><div class="meters" id="meters"></div></a>'
PAGE_TEMPLATE = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{{title}} — Mihai Cosma</title>
    <link rel="canonical" href="{{canonical_url}}">
    <link rel="stylesheet" href="/style.css">
</head>
<body>
{SITE_HEADER}
{METERS}
    <article class="post">
        <h1>{{title}}</h1>
{{body}}
    </article>
    <script src="/meters.js"></script>
    <script src="/site-nav.js"></script>
</body>
</html>
"""


class ArtifactError(ValueError):
    pass


def validate_complete_html(path: Path, relative: Path) -> None:
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as error:
        raise ArtifactError(f"HTML is not valid UTF-8 ({relative}): {error}") from error
    normalized = content.lstrip("\ufeff \t\r\n").lower()
    if (
        not normalized.startswith("<!doctype html")
        or "<html" not in normalized
        or "</html>" not in normalized
    ):
        raise ArtifactError(f"artifact is not complete HTML: {relative}")


def render_markdown(path: Path, relative: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as error:
        raise ArtifactError(f"Markdown is not valid UTF-8 ({relative}): {error}") from error
    title_match = re.match(r"#\s+(.+)", text)
    if not title_match:
        raise ArtifactError(f"{relative}: first line must be '# Title'")
    title = title_match.group(1).strip()
    body = markdown.markdown(
        text[title_match.end() :].lstrip("\n"),
        extensions=["fenced_code", "tables", "toc"],
        extension_configs={"toc": {"separator": "_"}},
    )
    output_relative = relative.with_suffix(".html")
    public_path = output_relative.as_posix()
    canonical_path = (
        "/inquisition/"
        if public_path == "index.html"
        else f"/inquisition/{quote(public_path)}"
    )
    return PAGE_TEMPLATE.format(
        title=html.escape(title),
        canonical_url=f"https://mihaicosma.com{canonical_path}",
        body=body,
    )


def build(source: Path, destination: Path) -> int:
    if source.is_symlink() or not source.is_dir():
        raise ArtifactError(f"artifact root must be a regular directory: {source}")

    paths = list(source.rglob("*"))
    targets: dict[Path, Path] = {}
    for path in paths:
        relative = path.relative_to(source)
        if any(part.startswith(".") for part in relative.parts):
            raise ArtifactError(f"artifact contains a hidden path: {relative}")
        if path.is_symlink():
            raise ArtifactError(f"artifact contains a symlink: {relative}")
        if not path.is_file() and not path.is_dir():
            raise ArtifactError(f"artifact contains a special file: {relative}")
        if path.is_dir():
            continue
        target = relative.with_suffix(".html") if path.suffix.lower() == ".md" else relative
        if target in targets:
            raise ArtifactError(
                f"artifact output collision: {targets[target]} and {relative} both produce {target}"
            )
        targets[target] = relative

    if Path("index.html") not in targets:
        raise ArtifactError("artifact requires prototype/index.html or prototype/index.md")

    destination.mkdir(parents=True, exist_ok=True)
    for path in paths:
        if path.is_dir():
            (destination / path.relative_to(source)).mkdir(parents=True, exist_ok=True)

    for target, relative in targets.items():
        source_path = source / relative
        destination_path = destination / target
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        if source_path.suffix.lower() == ".md":
            destination_path.write_text(
                render_markdown(source_path, relative), encoding="utf-8"
            )
        else:
            if source_path.suffix.lower() == ".html":
                validate_complete_html(source_path, relative)
            shutil.copy2(source_path, destination_path)
    return len(targets)


def main() -> int:
    if len(sys.argv) != 3:
        print(f"Usage: {Path(sys.argv[0]).name} SOURCE DESTINATION", file=sys.stderr)
        return 2
    try:
        count = build(Path(sys.argv[1]), Path(sys.argv[2]))
    except (ArtifactError, OSError) as error:
        print(f"Inquisition artifact error: {error}", file=sys.stderr)
        return 1
    print(f"staged {count} Inquisition prototype file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
