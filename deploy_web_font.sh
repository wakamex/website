#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

remote="mc-new"
zone="us-central1-a"
font="D2CodingLigature-web.woff2"
config="apache-font-preload.conf"

gcloud compute scp "$font" "$config" "$remote:~" --zone="$zone" --quiet

gcloud compute ssh "$remote" --zone="$zone" --quiet --command="
    set -e
    sudo install -m 644 '$font' '/var/www/mihaicosma.com/$font.new'
    sudo mv -- '/var/www/mihaicosma.com/$font.new' '/var/www/mihaicosma.com/$font'
    sudo install -m 644 '$config' '/etc/apache2/conf-available/mihaicosma-font-preload.conf'
    sudo a2enconf mihaicosma-font-preload >/dev/null
    sudo apache2ctl configtest
    sudo systemctl reload apache2
"

echo "Web font and preload header deployed"
