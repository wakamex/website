#!/usr/bin/env bash
set -u

cd "$(dirname "$0")"

source_dir=/code/inquisition/prototype
idle_seconds=${1:-5}
temporary_file_pattern='(^|/)[^/]*\.tmp\.[^/]*$'

if ! [[ "$idle_seconds" =~ ^[1-9][0-9]*$ ]]; then
    echo "Usage: $0 [positive-idle-seconds]" >&2
    exit 2
fi
if ! command -v inotifywait >/dev/null 2>&1; then
    echo "inotifywait is required" >&2
    exit 1
fi

publish() {
    echo "[$(date +%H:%M:%S)] Publishing Inquisition prototype..."
    if ./deploy.sh --inquisition; then
        echo "[$(date +%H:%M:%S)] Inquisition prototype is current"
    else
        echo "[$(date +%H:%M:%S)] Publish failed; watching for the next change" >&2
    fi
}

publish
echo "Watching $source_dir; publishing after $idle_seconds quiet second(s). Press Ctrl-C to stop."

while true; do
    if ! inotifywait -q -r --exclude "$temporary_file_pattern" \
        -e close_write,create,delete,move "$source_dir"; then
        sleep 1
        continue
    fi
    while inotifywait -q -r -t "$idle_seconds" --exclude "$temporary_file_pattern" \
        -e close_write,create,delete,move "$source_dir"; do
        :
    done
    publish
done
