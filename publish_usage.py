#!/usr/bin/env python3
"""Publish quota data from the local usage daemon caches as usage.json on the website.

The daemons replace their cache files rather than rewriting them, so the publisher polls file
contents instead of watching inodes. It uploads only when the published document changes and
retries a failed upload on the next poll.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

CACHES = {
    "claude": Path.home() / ".claude" / "usage-limits.json",
    "codex": Path.home() / ".codex" / "usage-limits.json",
    "agy": Path.home() / ".gemini" / "antigravity-cli" / "usage-limits.json",
    "zcode": Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "zcode-cli-usage" / "usage.json",
}
# Antigravity's cache also records command history, workspaces and the cloud project; publish only quota fields.
AGY_FIELDS = {"plan", "source", "updated_at", "status", "unavailable", "quota_summary", "quota_summary_error"}
AGY_SUMMARY_FIELDS = {"plan", "groups"}
PARSYNC = Path("/code/parsync-local-to-remote/target/release/parsync")
REMOTE = "mc:/var/www/mihaicosma.com"
POLL_SECONDS = 15


def public_document() -> dict:
    document = {}
    for key, path in CACHES.items():
        try:
            data = json.loads(path.read_text())
        except FileNotFoundError:
            continue
        except (OSError, json.JSONDecodeError) as error:
            # A daemon may be mid-write; keep the rest of the document and catch up on the next poll.
            log(f"skipping unreadable {key} cache: {error}")
            continue
        if key == "agy":
            data = {field: value for field, value in data.items() if field in AGY_FIELDS}
            if isinstance(data.get("quota_summary"), dict):
                data["quota_summary"] = {
                    field: value for field, value in data["quota_summary"].items() if field in AGY_SUMMARY_FIELDS
                }
        document[key] = data
    return document


def render(document: dict) -> str:
    return json.dumps(document, sort_keys=True)


def upload(content: str) -> None:
    with tempfile.TemporaryDirectory() as stage:
        (Path(stage) / "usage.json").write_text(content)
        result = subprocess.run(
            [str(PARSYNC), "-r", f"{stage}/usage.json", REMOTE],
            capture_output=True,
            text=True,
            timeout=120,
        )
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout).strip() or f"parsync exited {result.returncode}")


def log(message: str) -> None:
    print(f"[{datetime.now():%H:%M:%S}] {message}", file=sys.stderr, flush=True)


def daemon() -> None:
    published = None
    while True:
        content = render(public_document())
        if content != published:
            try:
                upload(content)
            except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
                log(f"upload failed, retrying in {POLL_SECONDS}s: {error}")
            else:
                published = content
                log("published")
        time.sleep(POLL_SECONDS)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--daemon", action="store_true", help="poll the caches and publish every change")
    group.add_argument("--write", type=Path, metavar="PATH", help="write the public document to PATH instead of uploading")
    args = parser.parse_args()
    if args.daemon:
        daemon()
    elif args.write:
        args.write.write_text(render(public_document()))
    else:
        upload(render(public_document()))
        log("published")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
