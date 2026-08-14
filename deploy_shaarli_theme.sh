#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

python3 build_shared_site.py

remote="mc-new"
zone="us-central1-a"
source_file="shaarli-theme/refined.css"
plugin_dir="shaarli-theme/site_navigation"
remote_root="/var/www/mihaicosma.com/links"
target="$remote_root/data/user.css"

remote_tmp=$(gcloud compute ssh "$remote" --zone="$zone" --quiet \
    --command='mktemp -d /tmp/shaarli-theme.XXXXXX')

cleanup() {
    gcloud compute ssh "$remote" --zone="$zone" --quiet \
        --command="rm -rf -- '$remote_tmp'" >/dev/null 2>&1 || true
}
trap cleanup EXIT

gcloud compute scp \
    "$source_file" \
    "$plugin_dir/site_navigation.php" \
    "$plugin_dir/site_navigation.meta" \
    "$plugin_dir/navigation.generated.php" \
    "$remote:$remote_tmp" \
    --zone="$zone" --quiet

gcloud compute ssh "$remote" --zone="$zone" --quiet --command="
    set -e
    test -d '$remote_root'
    php -l '$remote_tmp/site_navigation.php'
    php -l '$remote_tmp/navigation.generated.php'
    sudo install -d -m 755 -o www-data -g www-data '$remote_root/plugins/site_navigation'
    sudo install -m 644 -o www-data -g www-data '$remote_tmp/site_navigation.php' \
        '$remote_root/plugins/site_navigation/site_navigation.php'
    sudo install -m 644 -o www-data -g www-data '$remote_tmp/site_navigation.meta' \
        '$remote_root/plugins/site_navigation/site_navigation.meta'
    sudo install -m 644 -o www-data -g www-data '$remote_tmp/navigation.generated.php' \
        '$remote_root/plugins/site_navigation/navigation.generated.php'
    sudo install -m 644 -o www-data -g www-data '$remote_tmp/refined.css' '$target.new'
    sudo mv -- '$target.new' '$target'
    stat -c '%a %U:%G %s %n' '$target'
"

echo "Shaarli Refined theme deployed"
