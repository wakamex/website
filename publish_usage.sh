#!/bin/bash
set -e

# Generate usage.json from daemon caches and deploy to server
CLAUDE=~/.claude/usage-limits.json
CODEX=~/.codex/usage-limits.json
AGY=~/.gemini/antigravity-cli/usage-limits.json
OUT=/tmp/usage.json
PARSYNC=/code/parsync-local-to-remote/target/release/parsync
REMOTE=mc:/var/www/mihaicosma.com

if [ ! -x "$PARSYNC" ]; then
    echo "Missing executable parsync branch build: $PARSYNC" >&2
    exit 1
fi

publish() {
    python3 -c "
import json, sys, pathlib
out = {}
for key, path in [('claude', '$CLAUDE'), ('codex', '$CODEX'), ('agy', '$AGY')]:
    p = pathlib.Path(path)
    if p.exists():
        out[key] = json.loads(p.read_text())
json.dump(out, sys.stdout)
" > "$OUT"

    "$PARSYNC" -rP --verify-existing "$OUT" "$REMOTE" >/dev/null 2>&1
    echo "[$(date +%H:%M:%S)] published"
}

if [ "$1" = "-daemon" ]; then
    publish
    inotifywait -m -e close_write "$CLAUDE" "$CODEX" "$AGY" 2>/dev/null | while read -r _dir _event _file; do
        # Coalesce near-simultaneous cache writes from both daemons.
        sleep 1
        publish
    done
else
    publish
fi
