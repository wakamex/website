#!/bin/bash
set -e
cd "$(dirname "$0")"

python3 build_shared_site.py
python3 build_blog.py
python3 build_autoresearch.py --allow-stale-cache

python3 publish_usage.py --write usage.json

port=8001
while ! python3 -c "import socket,sys; s=socket.socket(); s.bind(('0.0.0.0', int(sys.argv[1])))" "$port" 2>/dev/null; do
    port=$((port+1))
done

ip=$(hostname -I | awk '{print $1}')
echo "Serving on http://localhost:$port and http://$ip:$port (LAN)"
exec python3 lan_server.py "$port"
