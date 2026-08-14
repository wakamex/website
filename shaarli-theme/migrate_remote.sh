#!/usr/bin/env bash
set -Eeuo pipefail

stage=${1:?staging directory is required}
old_root="/var/www/mihaicosma.com/shaarli"
new_root="/var/www/mihaicosma.com/links"
redirect_available="/etc/apache2/conf-available/mihaicosma-links.conf"
redirect_enabled="/etc/apache2/conf-enabled/mihaicosma-links.conf"
rollback_dir="/srv/shaarli-links-migration-$(date -u +%Y%m%dT%H%M%SZ)"
moved=0
redirect_installed=0
health_file=""

rollback() {
    status=$?
    trap - ERR
    echo "Migration failed, restoring /shaarli" >&2
    if [[ -n "$health_file" && -s "$health_file" && -d "$rollback_dir" ]]; then
        cp "$health_file" "$rollback_dir/failed-health.html"
    fi
    systemctl stop apache2 >/dev/null 2>&1 || true

    if [[ $moved -eq 1 && -d "$new_root" && ! -e "$old_root" ]]; then
        mv -- "$new_root" "$old_root"
    fi
    if [[ -d "$old_root" && -d "$rollback_dir" ]]; then
        install -m 640 -o www-data -g www-data \
            "$rollback_dir/config.json.php" "$old_root/data/config.json.php"
        install -m 644 -o www-data -g www-data \
            "$rollback_dir/user.css" "$old_root/data/user.css"
        rm -rf -- "$old_root/plugins/site_navigation"
    fi
    if [[ $redirect_installed -eq 1 ]]; then
        a2disconf mihaicosma-links >/dev/null 2>&1 || true
        rm -f -- "$redirect_available" "$redirect_enabled"
    fi

    apache2ctl configtest >/dev/null 2>&1 || true
    systemctl start apache2 >/dev/null 2>&1 || true
    exit "$status"
}
trap rollback ERR

echo "[1/5] Checking migration inputs and current installation..."
test -d "$old_root"
test ! -e "$new_root"
test ! -e "$redirect_available"
test ! -e "$redirect_enabled"
test ! -e "$old_root/plugins/site_navigation"
test -s "$stage/refined.css"
test -s "$stage/site_navigation.php"
test -s "$stage/site_navigation.meta"
test -s "$stage/navigation.generated.php"
test -s "$stage/configure_links.php"
test -s "$stage/apache-links-redirect.conf"
php -l "$stage/site_navigation.php" >/dev/null
php -l "$stage/navigation.generated.php" >/dev/null
php -l "$stage/configure_links.php" >/dev/null
apache2ctl configtest >/dev/null

mkdir -m 700 "$rollback_dir"
install -m 600 "$old_root/data/config.json.php" "$rollback_dir/config.json.php"
install -m 600 "$old_root/data/user.css" "$rollback_dir/user.css"
datastore_hash=$(sha256sum "$old_root/data/datastore.php" | cut -d' ' -f1)

echo "[2/5] Stopping Apache and installing the compatibility redirect..."
systemctl stop apache2
install -m 644 "$stage/apache-links-redirect.conf" "$redirect_available"
a2enconf mihaicosma-links >/dev/null
redirect_installed=1
apache2ctl configtest >/dev/null

echo "[3/5] Moving Shaarli to /links and installing navigation assets..."
mv -- "$old_root" "$new_root"
moved=1
install -d -m 755 -o www-data -g www-data "$new_root/plugins/site_navigation"
install -m 644 -o www-data -g www-data \
    "$stage/site_navigation.php" "$new_root/plugins/site_navigation/site_navigation.php"
install -m 644 -o www-data -g www-data \
    "$stage/site_navigation.meta" "$new_root/plugins/site_navigation/site_navigation.meta"
install -m 644 -o www-data -g www-data \
    "$stage/navigation.generated.php" "$new_root/plugins/site_navigation/navigation.generated.php"
install -m 644 -o www-data -g www-data "$stage/refined.css" "$new_root/data/user.css"

php "$stage/configure_links.php" "$new_root"
chown --reference="$new_root/data/config.json.php" "$new_root/data/config.json.php.new"
chmod --reference="$new_root/data/config.json.php" "$new_root/data/config.json.php.new"
mv -- "$new_root/data/config.json.php.new" "$new_root/data/config.json.php"
find "$new_root/tmp" -mindepth 1 ! -name .htaccess -delete
test "$datastore_hash" = "$(sha256sum "$new_root/data/datastore.php" | cut -d' ' -f1)"

echo "[4/5] Starting Apache and checking the new application path..."
systemctl start apache2
health_file=$(mktemp /tmp/shaarli-links-health.XXXXXX)
trap 'rm -f -- "$health_file"' EXIT
curl -fkSs --resolve mihaicosma.com:443:127.0.0.1 \
    -o "$health_file" https://mihaicosma.com/links/
if ! grep -q 'site-navigation-links' "$health_file"; then
    echo "Health check failed: global navigation marker is missing" >&2
    false
fi
if ! grep -q 'site-navigation-all' "$health_file"; then
    echo "Health check failed: local navigation marker is missing" >&2
    false
fi

echo "[5/5] Checking the permanent legacy redirect..."
legacy_status=$(curl -sk -o /dev/null -w '%{http_code}' \
    --resolve mihaicosma.com:443:127.0.0.1 \
    https://mihaicosma.com/shaarli/shaare/F9zemw)
legacy_location=$(curl -skI --resolve mihaicosma.com:443:127.0.0.1 \
    https://mihaicosma.com/shaarli/shaare/F9zemw \
    | awk 'tolower($1) == "location:" {print $2}' | tr -d '\r')
test "$legacy_status" = 308
test "$legacy_location" = "https://mihaicosma.com/links/shaare/F9zemw" \
    -o "$legacy_location" = "/links/shaare/F9zemw"
test "$datastore_hash" = "$(sha256sum "$new_root/data/datastore.php" | cut -d' ' -f1)"
systemctl is-active --quiet apache2

rm -f -- "$health_file"
trap - EXIT
trap - ERR
echo "Shaarli is live at /links/"
echo "Rollback metadata: $rollback_dir"
