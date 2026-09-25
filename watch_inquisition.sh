#!/usr/bin/env bash
set -u

cd "$(dirname "$0")"

source_dir=/code/inquisition/prototype
idle_seconds=${1:-5}
retry_seconds=30
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
        return 0
    else
        echo "[$(date +%H:%M:%S)] Publish failed; watching for the next change" >&2
        return 1
    fi
}

source_version() {
    find "$source_dir" -type f ! -name '*.tmp.*' -print0 \
        | sort -z \
        | xargs -0 -r sha256sum --zero \
        | sha256sum \
        | cut -d ' ' -f 1
}

wait_for_source_quiet() {
    previous_version=$(source_version)
    while true; do
        sleep "$idle_seconds"
        current_version=$(source_version)
        if [ "$current_version" = "$previous_version" ]; then
            return
        fi
        previous_version=$current_version
    done
}

deployed_version=
publish_current_version() {
    while true; do
        candidate_version=$(source_version)
        if ! publish; then
            echo "[$(date +%H:%M:%S)] Retrying publish in $retry_seconds seconds"
            sleep "$retry_seconds"
            continue
        fi
        current_version=$(source_version)
        if [ "$current_version" = "$candidate_version" ]; then
            deployed_version=$current_version
            return
        fi
        echo "[$(date +%H:%M:%S)] Source changed during publish; waiting for a quiet tree before catching up"
        wait_for_source_quiet
    done
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
        publish_current_version

        while IFS= read -r event; do
            while IFS= read -r -t "$idle_seconds" event; do
                :
            done
            current_version=$(source_version)
            if [ "$current_version" != "$deployed_version" ]; then
                publish_current_version
            fi
        done
    }
    echo "Inquisition file monitor stopped; restarting" >&2
    sleep 1
done
