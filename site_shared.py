"""Shared navigation and header-theme generation."""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).parent
NAVIGATION_PATH = ROOT / "site-navigation.json"
THEME_PATH = ROOT / "site-theme.css"
NAVIGATION_START = "<!-- GENERATED SITE NAVIGATION:START active={active} -->"
NAVIGATION_END = "<!-- GENERATED SITE NAVIGATION:END -->"
THEME_START = "/* GENERATED SITE HEADER THEME:START */"
THEME_END = "/* GENERATED SITE HEADER THEME:END */"


class SharedSiteError(ValueError):
    """Canonical site navigation or theme data is invalid."""


def load_navigation() -> list[dict[str, str]]:
    data: Any = json.loads(NAVIGATION_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not data:
        raise SharedSiteError("site-navigation.json must contain a non-empty list")

    navigation: list[dict[str, str]] = []
    slugs: set[str] = set()
    for index, item in enumerate(data):
        if not isinstance(item, dict) or set(item) != {"slug", "href", "label"}:
            raise SharedSiteError(
                f"navigation item {index} must contain only slug, href, and label"
            )
        if not all(isinstance(item[field], str) and item[field] for field in item):
            raise SharedSiteError(f"navigation item {index} has an empty or non-string value")
        if item["slug"] in slugs:
            raise SharedSiteError(f"duplicate navigation slug: {item['slug']}")
        slugs.add(item["slug"])
        navigation.append(item)
    return navigation


def render_site_header(active: str | None) -> str:
    navigation = load_navigation()
    navigation_slugs = {item["slug"] for item in navigation}
    if active is not None and active not in navigation_slugs:
        raise SharedSiteError(f"unknown active navigation slug: {active}")

    def render_links(items: list[dict[str, str]], indent: str) -> list[str]:
        links = []
        for item in items:
            attributes = [
                f'href="{html.escape(item["href"], quote=True)}"',
                f'class="site-navigation-link site-navigation-{html.escape(item["slug"], quote=True)}"',
            ]
            if item["slug"] == active:
                attributes.append('aria-current="page"')
            links.append(
                f"{indent}<a {' '.join(attributes)}>{html.escape(item['label'])}</a>"
            )
        return links

    return "\n".join(
        [
            NAVIGATION_START.format(active=active or "none"),
            '    <header class="site-header">',
            '      <a class="site-header-title" href="/">Mihai Cosma</a>',
            '      <button class="site-header-toggle" type="button" aria-controls="site-navigation" aria-expanded="false" aria-label="Menu" hidden><span class="bar"></span><span class="bar"></span></button>',
            '      <nav class="links links-top" id="site-navigation" aria-label="Main navigation">',
            *render_links(navigation, "        "),
            "      </nav>",
            "    </header>",
            NAVIGATION_END,
        ]
    )


def render_shaarli_navigation() -> str:
    def php_string(value: str) -> str:
        return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"

    rows = ["<?php", "", "// Generated from site-navigation.json. Do not edit.", "return ["]
    for item in load_navigation():
        rows.append(
            "    ["
            + ", ".join(
                f"{php_string(field)} => {php_string(item[field])}"
                for field in ("slug", "href", "label")
            )
            + "],"
        )
    rows.extend(["];", ""])
    return "\n".join(rows)


def render_theme(target: str) -> str:
    sections: dict[str, list[str]] = {"common": [], "static": [], "shaarli": []}
    current: str | None = None
    for line in THEME_PATH.read_text(encoding="utf-8").splitlines():
        if line.startswith("/* @target ") and line.endswith(" */"):
            current = line.removeprefix("/* @target ").removesuffix(" */")
            if current not in sections:
                raise SharedSiteError(f"unknown site-theme.css target: {current}")
            continue
        if current is None:
            if line.strip():
                raise SharedSiteError("site-theme.css content appears before a target marker")
            continue
        sections[current].append(line)

    if target not in {"static", "shaarli"}:
        raise SharedSiteError(f"unknown theme output target: {target}")

    content = "\n".join(sections[target] + sections["common"]).strip()
    if target == "shaarli":
        order_rules = []
        for order, item in enumerate(load_navigation(), start=1):
            order_rules.extend(
                [
                    f'    .shaarli-menu .menu-transform > .pure-menu-list > li:has(> .site-navigation-{item["slug"]}) {{',
                    f"        order: {order};",
                    "    }",
                    "",
                ]
            )
        content = content.replace(
            "/* {{NAVIGATION_ORDER_RULES}} */", "\n".join(order_rules).rstrip()
        )
    return "/* Generated from site-theme.css. Do not edit this block. */\n" + content


def replace_generated_block(content: str, start: str, end: str, generated: str) -> str:
    if content.count(start) != 1 or content.count(end) != 1:
        raise SharedSiteError(f"expected exactly one generated block: {start}")
    before, remainder = content.split(start, 1)
    _, after = remainder.split(end, 1)
    return f"{before}{start}\n{generated}\n{end}{after}"


def write_if_changed(path: Path, content: str) -> None:
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return
    path.write_text(content, encoding="utf-8")
