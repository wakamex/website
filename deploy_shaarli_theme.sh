#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

python3 build_shared_site.py

remote="mc-new"
zone="us-central1-a"
source_file="shaarli-theme/refined.css"
template_patcher="shaarli-theme/patch_linklist.py"
css_bundler="shaarli-theme/build_css_bundle.py"
icon_patcher="shaarli-theme/inline_svg_icons.py"
plugin_dir="shaarli-theme/site_navigation"
remote_root="/var/www/mihaicosma.com/links"

remote_tmp=$(gcloud compute ssh "$remote" --zone="$zone" --quiet \
    --command='mktemp -d /tmp/shaarli-theme.XXXXXX')

cleanup() {
    gcloud compute ssh "$remote" --zone="$zone" --quiet \
        --command="rm -rf -- '$remote_tmp'" >/dev/null 2>&1 || true
}
trap cleanup EXIT

gcloud compute scp \
    "$source_file" \
    "$template_patcher" \
    "$css_bundler" \
    "$icon_patcher" \
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
    sudo python3 '$remote_tmp/patch_linklist.py' \
        '$remote_root/tpl/default/linklist.html'
    sudo python3 '$remote_tmp/inline_svg_icons.py' '$remote_root'
    sudo python3 '$remote_tmp/build_css_bundle.py' \
        '$remote_root' '$remote_tmp/refined.css'
    sudo rm -f -- '$remote_root/data/user.css'
    sudo install -d -m 755 -o www-data -g www-data '$remote_root/plugins/site_navigation'
    sudo install -m 644 -o www-data -g www-data '$remote_tmp/site_navigation.php' \
        '$remote_root/plugins/site_navigation/site_navigation.php'
    sudo install -m 644 -o www-data -g www-data '$remote_tmp/site_navigation.meta' \
        '$remote_root/plugins/site_navigation/site_navigation.meta'
    sudo install -m 644 -o www-data -g www-data '$remote_tmp/navigation.generated.php' \
        '$remote_root/plugins/site_navigation/navigation.generated.php'
    stat -c '%a %U:%G %s %n' \
        '$remote_root/tpl/default/css/site-refined.css' \
        '$remote_root/tpl/default/includes.html'
    curl -fkSs --resolve mihaicosma.com:443:127.0.0.1 \
        -o '$remote_tmp/health.html' https://mihaicosma.com/links/
    grep -q '/links/tpl/default/css/site-refined.css?v=' '$remote_tmp/health.html'
    ! grep -Eq '/links/(tpl/default/css/(shaarli|markdown)\.min\.css|data/user\.css)' \
        '$remote_tmp/health.html'
    curl -fkSs --resolve mihaicosma.com:443:127.0.0.1 \
        -o '$remote_tmp/site-refined.css' \
        https://mihaicosma.com/links/tpl/default/css/site-refined.css
    grep -q 'mihaicosma.com refinements' '$remote_tmp/site-refined.css'
    ! grep -q 'forkawesome-webfont' '$remote_tmp/site-refined.css'
    grep -q 'GENERATED INLINE ICON SPRITE:START' '$remote_tmp/health.html'
    ! grep -Eq '<i[^>]+class=.[^>]*fa-' '$remote_tmp/health.html'
"

echo "Shaarli Refined theme deployed"
