#!/bin/bash
# Generate usage.json from daemon caches and deploy to server
CLAUDE=~/.claude/usage-limits.json
CODEX=~/.codex/usage-limits.json
OUT=/tmp/usage.json

publish() {
    python3 -c "
import json, sys, pathlib
out = {}
for key, path in [('claude', '$CLAUDE'), ('codex', '$CODEX')]:
    p = pathlib.Path(path)
    if p.exists():
        out[key] = json.loads(p.read_text())
json.dump(out, sys.stdout)
" > "$OUT"

    gcloud compute scp "$OUT" mc-new:~ --zone=us-central1-a 2>/dev/null
    gcloud compute ssh mc-new --zone=us-central1-a --command="sudo mv ~/usage.json /var/www/mihaicosma.com/" 2>/dev/null
    echo "[$(date +%H:%M:%S)] published"
}

if [ "$1" = "-daemon" ]; then
    publish
    inotifywait -m -e close_write "$CLAUDE" "$CODEX" 2>/dev/null | while read -r _dir _event _file; do
        publish
    done
else
    publish
fi
