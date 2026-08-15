#!/usr/bin/env python3
"""Build the Autoresearch collection and the featured homepage section."""

from __future__ import annotations

import argparse
import html
import json
import os
import sys
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from site_shared import render_site_header


ROOT = Path(__file__).parent
DEFAULT_SOURCE = (
    "https://raw.githubusercontent.com/wakamex/autoresearch/master/"
    "learnings/case-studies/case-studies.json"
)
SUPPORTED_SCHEMA_VERSIONS = {2}
START_MARKER = "    <!-- AUTORESEARCH:START -->"
END_MARKER = "    <!-- AUTORESEARCH:END -->"

ROOT_FIELDS = {
    "schema_version": int,
    "title": str,
    "description": str,
    "updated": str,
    "repository_url": str,
    "token_estimates": dict,
    "cases": list,
}
CASE_FIELDS = {
    "case": int,
    "slug": str,
    "filename": str,
    "title": str,
    "started": str,
    "ended": str,
    "summary_markdown": str,
    "summary_text": str,
    "word_count": int,
    "token_estimate": dict,
    "report_url": str,
    "raw_url": str,
}


class FeedError(ValueError):
    """The case-study feed is malformed or unsafe to render."""


def require_fields(value: dict[str, Any], fields: dict[str, type], context: str) -> None:
    for name, expected_type in fields.items():
        if name not in value:
            raise FeedError(f"{context}: missing required field {name!r}")
        if type(value[name]) is not expected_type:
            raise FeedError(
                f"{context}.{name}: expected {expected_type.__name__}, "
                f"got {type(value[name]).__name__}"
            )


def parse_date(value: str, context: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise FeedError(f"{context}: expected a valid ISO date, got {value!r}") from exc


def validate_url(value: str, context: str) -> None:
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise FeedError(f"{context}: expected a safe HTTP or HTTPS URL, got {value!r}")


def validate_feed(data: Any) -> dict[str, Any]:
    if type(data) is not dict:
        raise FeedError(f"feed root: expected object, got {type(data).__name__}")
    require_fields(data, ROOT_FIELDS, "feed")

    if data["schema_version"] not in SUPPORTED_SCHEMA_VERSIONS:
        raise FeedError(f"feed.schema_version: unsupported value {data['schema_version']!r}")
    for field in ("title", "description"):
        if not data[field]:
            raise FeedError(f"feed.{field}: expected a non-empty string")
    parse_date(data["updated"], "feed.updated")
    validate_url(data["repository_url"], "feed.repository_url")

    token_estimates = data["token_estimates"]
    require_fields(
        token_estimates,
        {"processed_tokens": int, "effective_tokens": int, "method": str},
        "feed.token_estimates",
    )
    if set(token_estimates) != {"processed_tokens", "effective_tokens", "method"}:
        raise FeedError("feed.token_estimates: unexpected fields")
    for field in ("processed_tokens", "effective_tokens"):
        if token_estimates[field] < 0:
            raise FeedError(f"feed.token_estimates.{field}: expected a non-negative integer")
    if token_estimates["effective_tokens"] > token_estimates["processed_tokens"]:
        raise FeedError("feed.token_estimates: effective tokens exceed processed tokens")
    if not token_estimates["method"].strip():
        raise FeedError("feed.token_estimates.method: expected a non-empty string")

    case_numbers: set[int] = set()
    slugs: set[str] = set()
    featured_ranks: set[int] = set()

    for index, case in enumerate(data["cases"]):
        context = f"feed.cases[{index}]"
        if type(case) is not dict:
            raise FeedError(f"{context}: expected object, got {type(case).__name__}")
        require_fields(case, CASE_FIELDS, context)
        if "featured_rank" not in case:
            raise FeedError(f"{context}: missing required field 'featured_rank'")

        if case["case"] <= 0:
            raise FeedError(f"{context}.case: expected a positive integer")
        for field in ("slug", "filename", "title", "summary_markdown", "summary_text"):
            if not case[field]:
                raise FeedError(f"{context}.{field}: expected a non-empty string")
        if case["case"] in case_numbers:
            raise FeedError(f"{context}.case: duplicate case number {case['case']}")
        if case["slug"] in slugs:
            raise FeedError(f"{context}.slug: duplicate slug {case['slug']!r}")
        case_numbers.add(case["case"])
        slugs.add(case["slug"])

        started = parse_date(case["started"], f"{context}.started")
        ended = parse_date(case["ended"], f"{context}.ended")
        if started > ended:
            raise FeedError(f"{context}: started date is after ended date")
        if case["word_count"] <= 0:
            raise FeedError(f"{context}.word_count: expected a positive integer")

        token_estimate = case["token_estimate"]
        require_fields(
            token_estimate,
            {"processed_tokens": int, "effective_tokens": int, "confidence": str},
            f"{context}.token_estimate",
        )
        expected_token_fields = {"processed_tokens", "effective_tokens", "confidence"}
        if set(token_estimate) != expected_token_fields:
            raise FeedError(f"{context}.token_estimate: unexpected fields")
        for field in ("processed_tokens", "effective_tokens"):
            if token_estimate[field] < 0:
                raise FeedError(
                    f"{context}.token_estimate.{field}: expected a non-negative integer"
                )
        if token_estimate["effective_tokens"] > token_estimate["processed_tokens"]:
            raise FeedError(f"{context}.token_estimate: effective tokens exceed processed tokens")
        if token_estimate["confidence"] not in {"high", "medium", "low"}:
            raise FeedError(
                f"{context}.token_estimate.confidence: expected high, medium, or low"
            )

        rank = case.get("featured_rank")
        if rank is not None:
            if type(rank) is not int or rank <= 0:
                raise FeedError(f"{context}.featured_rank: expected null or a positive integer")
            if rank in featured_ranks:
                raise FeedError(f"{context}.featured_rank: duplicate featured rank {rank}")
            featured_ranks.add(rank)

        validate_url(case["report_url"], f"{context}.report_url")
        validate_url(case["raw_url"], f"{context}.raw_url")

        links = case.get("links", [])
        if type(links) is not list:
            raise FeedError(f"{context}.links: expected a list when present")
        for link_index, link in enumerate(links):
            link_context = f"{context}.links[{link_index}]"
            if type(link) is not dict:
                raise FeedError(f"{link_context}: expected object, got {type(link).__name__}")
            require_fields(link, {"text": str, "url": str}, link_context)
            validate_url(link["url"], f"{link_context}.url")

    if not data["cases"]:
        raise FeedError("feed.cases: expected at least one case")
    return data


def decode_feed(raw: bytes, source: str) -> dict[str, Any]:
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FeedError(f"{source}: invalid UTF-8 JSON: {exc}") from exc
    return validate_feed(data)


def default_cache_path() -> Path:
    cache_root = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    return cache_root / "mihaicosma.com" / "autoresearch-case-studies.json"


def read_source(source: str, timeout: float = 20.0) -> bytes:
    parsed = urlsplit(source)
    if parsed.scheme in {"http", "https"}:
        request = Request(source, headers={"User-Agent": "mihaicosma.com autoresearch builder"})
        with urlopen(request, timeout=timeout) as response:
            return response.read()
    return Path(source).read_bytes()


def load_feed(
    source: str,
    *,
    allow_stale_cache: bool = False,
    cache_path: Path | None = None,
) -> tuple[dict[str, Any], bool, str | None]:
    cache_path = cache_path or default_cache_path()
    is_remote = urlsplit(source).scheme in {"http", "https"}
    try:
        raw = read_source(source)
        data = decode_feed(raw, source)
    except Exception as exc:
        if not (allow_stale_cache and is_remote and cache_path.exists()):
            raise FeedError(f"could not load a valid feed from {source}: {exc}") from exc
        try:
            data = decode_feed(cache_path.read_bytes(), str(cache_path))
        except Exception as cache_exc:
            raise FeedError(
                f"fresh feed failed ({exc}); cached feed is also invalid ({cache_exc})"
            ) from cache_exc
        warning = f"Fresh Autoresearch feed unavailable. Showing validated cached data. ({exc})"
        return data, True, warning

    if is_remote:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_cache = cache_path.with_suffix(f"{cache_path.suffix}.tmp")
        temporary_cache.write_bytes(raw)
        temporary_cache.replace(cache_path)
    return data, False, None


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def render_warning(warning: str | None) -> str:
    if warning is None:
        return ""
    return f'        <p class="build-warning" role="status">{esc(warning)}</p>\n'


def render_featured(data: dict[str, Any], warning: str | None = None) -> str:
    featured = sorted(
        (case for case in data["cases"] if case.get("featured_rank") is not None),
        key=lambda case: case["featured_rank"],
    )
    items = []
    for case in featured:
        items.append(
            f'''            <li><a href="{esc(case["report_url"])}">CASE {esc(case["case"])} ({esc(case["started"])})</a> {esc(case["summary_text"])}</li>'''
        )
    return f'''    <section class="featured-research" aria-labelledby="featured-research-title">
        <h2 id="featured-research-title">Featured Autoresearch</h2>
{render_warning(warning)}        <ul class="featured-research-list">
{chr(10).join(items)}
        </ul>
        <p class="research-collection-link"><a href="/autoresearch.html">View the full collection ({len(data["cases"])} cases) <span aria-hidden="true">-&gt;</span></a></p>
    </section>'''


def format_effective_tokens(tokens: int) -> str:
    if tokens >= 1_000_000_000:
        value = f"{tokens / 1_000_000_000:.2f}".rstrip("0").rstrip(".")
        return f"{value}B"
    if tokens >= 1_000_000:
        value = f"{tokens / 1_000_000:.1f}".rstrip("0").rstrip(".")
        return f"{value}M"
    if tokens >= 1_000:
        value = f"{tokens / 1_000:.1f}".rstrip("0").rstrip(".")
        return f"{value}K"
    return str(tokens)


def render_case(case: dict[str, Any]) -> str:
    effective_tokens = format_effective_tokens(
        case["token_estimate"]["effective_tokens"]
    )
    return f'''        <article class="research-entry" id="case-{esc(case["case"])}">
            <p class="research-summary"><a href="{esc(case["report_url"])}">CASE {esc(case["case"])}</a> {esc(case["summary_text"])}</p>
            <p class="research-meta">{esc(case["started"])} - {esc(case["ended"])} <span aria-hidden="true">/</span> {esc(effective_tokens)} effective tokens</p>
        </article>'''


def render_collection(data: dict[str, Any], warning: str | None = None) -> str:
    cases = sorted(data["cases"], key=lambda case: case["case"])
    first_started = min(case["started"] for case in cases)
    last_ended = max(case["ended"] for case in cases)
    entries = "\n".join(render_case(case) for case in cases)
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{esc(data["title"])} - Mihai Cosma</title>
    <meta name="description" content="{esc(data["description"])}">
    <link rel="stylesheet" href="/style.css">
</head>
<body>
{render_site_header("autoresearch")}
    <a href="/status.html" class="meters-link"><div class="meters" id="meters"></div></a>
    <main class="autoresearch">
        <header class="research-header">
            <h1>{esc(data["title"])}</h1>
            <p class="research-description">{esc(data["description"])}</p>
            <p class="research-overview">{len(cases)} cases <span aria-hidden="true">//</span> {esc(first_started)} - {esc(last_ended)}</p>
        </header>
{render_warning(warning)}        <div class="research-list research-list-complete">
{entries}
        </div>
    </main>
    <script src="/meters.js"></script>
    <script src="/site-nav.js"></script>
</body>
</html>
'''


def replace_featured(index_html: str, section: str) -> str:
    if index_html.count(START_MARKER) != 1 or index_html.count(END_MARKER) != 1:
        raise FeedError("index.html must contain exactly one pair of Autoresearch markers")
    before, remainder = index_html.split(START_MARKER, 1)
    _, after = remainder.split(END_MARKER, 1)
    return f"{before}{START_MARKER}\n{section}\n{END_MARKER}{after}"


def write_if_changed(path: Path, content: str) -> None:
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return
    path.write_text(content, encoding="utf-8")


def build(data: dict[str, Any], root: Path = ROOT, warning: str | None = None) -> None:
    data = validate_feed(data)
    index_path = root / "index.html"
    index_html = replace_featured(
        index_path.read_text(encoding="utf-8"), render_featured(data, warning)
    )
    write_if_changed(index_path, index_html)
    write_if_changed(root / "autoresearch.html", render_collection(data, warning))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        default=DEFAULT_SOURCE,
        help="HTTP(S) feed URL or local JSON fixture",
    )
    freshness = parser.add_mutually_exclusive_group()
    freshness.add_argument(
        "--allow-stale-cache",
        action="store_true",
        help="fall back to a validated cache and render a warning if a remote fetch fails",
    )
    freshness.add_argument(
        "--require-fresh",
        action="store_true",
        help="require the configured source to load and validate successfully",
    )
    parser.add_argument("--cache", type=Path, default=default_cache_path())
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        data, stale, warning = load_feed(
            args.source,
            allow_stale_cache=args.allow_stale_cache,
            cache_path=args.cache,
        )
        build(data, warning=warning)
    except (FeedError, OSError) as exc:
        print(f"autoresearch build failed: {exc}", file=sys.stderr)
        return 1
    if stale:
        print(f"WARNING: {warning}", file=sys.stderr)
    print(f"built {len(data['cases'])} Autoresearch case studies")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
