#!/bin/bash
set -e
cd "$(dirname "$0")"

python3 build_blog.py
python3 build_autoresearch.py --allow-stale-cache

python3 - <<'PY'
import json, pathlib
out = {}
for key, path in [
    ('claude', '~/.claude/usage-limits.json'),
    ('codex', '~/.codex/usage-limits.json'),
    ('agy', '~/.gemini/antigravity-cli/usage-limits.json'),
]:
    p = pathlib.Path(path).expanduser()
    if p.exists():
        out[key] = json.loads(p.read_text())
pathlib.Path('usage.json').write_text(json.dumps(out))
PY

port=8001
while ! python3 -c "import socket,sys; s=socket.socket(); s.bind(('0.0.0.0', int(sys.argv[1])))" "$port" 2>/dev/null; do
    port=$((port+1))
done

ip=$(hostname -I | awk '{print $1}')
echo "Serving on http://localhost:$port and http://$ip:$port (LAN)"
exec python3 -m http.server "$port" --bind 0.0.0.0
