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

watch_events() {
    LC_ALL=C inotifywait -m -r --format 'EVENT %w%f' \
        --exclude "$temporary_file_pattern" \
        -e close_write,create,delete,move "$source_dir" 2>&1
}

while true; do
    watch_events | {
        watches_ready=false
        while IFS= read -r event; do
            case "$event" in
                "Watches established.")
                    watches_ready=true
                    break
                    ;;
                "Setting up watches."*)
                    ;;
                *)
                    echo "$event" >&2
                    ;;
            esac
        done
        if ! $watches_ready; then
            exit 1
        fi

        echo "Watching $source_dir; publishing after $idle_seconds quiet second(s). Press Ctrl-C to stop."
        publish

        while IFS= read -r event; do
            while IFS= read -r -t "$idle_seconds" event; do
                :
            done
            publish
        done
    }
    echo "Inquisition file monitor stopped; restarting" >&2
    sleep 1
done
