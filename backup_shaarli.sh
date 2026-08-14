#!/usr/bin/env bash
set -euo pipefail

REMOTE="mc-new"
ZONE="us-central1-a"
REMOTE_PARENT="/var/www/mihaicosma.com"
REMOTE_NAME="shaarli"
BACKUP_DIR="/mnt/raid5/website/shaarli"

timestamp=$(date -u +%Y%m%dT%H%M%SZ)
archive_name="shaarli-$timestamp.tar.gz"

remote_tmp=""
local_tmp=""
partial=""

cleanup() {
    if [[ -n "$local_tmp" ]]; then
        rm -rf -- "$local_tmp"
    fi
    if [[ -n "$partial" ]]; then
        rm -f -- "$partial"
    fi
    if [[ -n "$remote_tmp" ]]; then
        gcloud compute ssh "$REMOTE" --zone="$ZONE" \
            --command="rm -rf -- '$remote_tmp'" >/dev/null 2>&1 || true
    fi
}
trap cleanup EXIT

echo "=== Shaarli backup: $(date -Iseconds) ==="
install -d -m 700 "$BACKUP_DIR"

echo "[1/4] Creating the remote snapshot..."
remote_tmp=$(gcloud compute ssh "$REMOTE" --zone="$ZONE" --quiet \
    --command='mktemp -d /tmp/shaarli-backup.XXXXXX')
remote_archive="$remote_tmp/$archive_name"
remote_restore="$remote_tmp/restore"

gcloud compute ssh "$REMOTE" --zone="$ZONE" --quiet --command="
    set -eu
    sudo tar --acls --xattrs --numeric-owner -C '$REMOTE_PARENT' -cpf - '$REMOTE_NAME' \
        | gzip -1 > '$remote_archive'
    chmod 600 '$remote_archive'
"

echo "[2/4] Testing a temporary restore on the server..."
gcloud compute ssh "$REMOTE" --zone="$ZONE" --quiet --command="
    set -eu
    gzip -t '$remote_archive'
    mkdir -m 700 '$remote_restore'
    tar -xzf '$remote_archive' -C '$remote_restore'
    test -s '$remote_restore/$REMOTE_NAME/index.php'
    test -s '$remote_restore/$REMOTE_NAME/shaarli_version.php'
    test -s '$remote_restore/$REMOTE_NAME/data/datastore.php'
    test -s '$remote_restore/$REMOTE_NAME/data/config.json.php'
    test -d '$remote_restore/$REMOTE_NAME/plugins'
    php -l '$remote_restore/$REMOTE_NAME/index.php' >/dev/null
    php -l '$remote_restore/$REMOTE_NAME/data/datastore.php' >/dev/null
"

remote_sha256=$(gcloud compute ssh "$REMOTE" --zone="$ZONE" --quiet \
    --command="sha256sum '$remote_archive' | cut -d' ' -f1")

echo "[3/4] Copying the verified snapshot to $BACKUP_DIR..."
partial="$BACKUP_DIR/.$archive_name.partial"
rm -f -- "$partial"
gcloud compute scp "$REMOTE:$remote_archive" "$partial" --zone="$ZONE" --quiet
chmod 600 "$partial"

local_sha256=$(sha256sum "$partial" | cut -d' ' -f1)
if [[ "$local_sha256" != "$remote_sha256" ]]; then
    echo "Backup checksum does not match the remote snapshot" >&2
    exit 1
fi

echo "[4/4] Testing a temporary restore from the local backup..."
local_tmp=$(mktemp -d)
chmod 700 "$local_tmp"
tar -xzf "$partial" -C "$local_tmp"
test -s "$local_tmp/$REMOTE_NAME/index.php"
test -s "$local_tmp/$REMOTE_NAME/shaarli_version.php"
test -s "$local_tmp/$REMOTE_NAME/data/datastore.php"
test -s "$local_tmp/$REMOTE_NAME/data/config.json.php"
test -d "$local_tmp/$REMOTE_NAME/plugins"

archive="$BACKUP_DIR/$archive_name"
mv -- "$partial" "$archive"
partial=""
printf '%s  %s\n' "$local_sha256" "$archive_name" > "$archive.sha256"
chmod 600 "$archive.sha256"

echo
echo "=== Backup and restore test complete ==="
du -h "$archive"
echo "SHA-256: $local_sha256"
echo "Archive: $archive"
