#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

python3 build_shared_site.py

remote="mc-new"
zone="us-central1-a"
asset_dir="shaarli-theme"
remote_tmp=$(gcloud compute ssh "$remote" --zone="$zone" --quiet \
    --command='mktemp -d /tmp/shaarli-links-migration.XXXXXX')

cleanup() {
    gcloud compute ssh "$remote" --zone="$zone" --quiet \
        --command="rm -rf -- '$remote_tmp'" >/dev/null 2>&1 || true
}
trap cleanup EXIT

gcloud compute scp \
    "$asset_dir/refined.css" \
    "$asset_dir/site_navigation/site_navigation.php" \
    "$asset_dir/site_navigation/site_navigation.meta" \
    "$asset_dir/site_navigation/navigation.generated.php" \
    "$asset_dir/configure_links.php" \
    "$asset_dir/apache-links-redirect.conf" \
    "$asset_dir/migrate_remote.sh" \
    "$remote:$remote_tmp" \
    --zone="$zone" --quiet

gcloud compute ssh "$remote" --zone="$zone" --quiet \
    --command="sudo /bin/bash '$remote_tmp/migrate_remote.sh' '$remote_tmp'"
