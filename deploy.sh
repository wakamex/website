#!/bin/bash
set -e
cd "$(dirname "$0")"

# Regenerate blog (idempotent, fast).
python3 build_shared_site.py
python3 build_blog.py
python3 build_autoresearch.py --require-fresh

# Top-level files: default set, or whatever the user passed.
files="${@:-index.html autoresearch.html projects.html style.css resume.html status.html blog.html og-image.png meters.js site-nav.js D2CodingLigature-web.woff2}"
gcloud compute scp $files mc-new:~ --zone=us-central1-a
for f in $files; do
    gcloud compute ssh mc-new --zone=us-central1-a --command="sudo mv ~/${f##*/} /var/www/mihaicosma.com/"
done

# Post HTML: only sync when running the default deploy (no args).
if [ $# -eq 0 ]; then
    post_files=(posts/*.html)
    if [ -e "${post_files[0]}" ]; then
        gcloud compute ssh mc-new --zone=us-central1-a --command="sudo mkdir -p /var/www/mihaicosma.com/posts"
        gcloud compute scp "${post_files[@]}" mc-new:~ --zone=us-central1-a
        for f in "${post_files[@]}"; do
            gcloud compute ssh mc-new --zone=us-central1-a --command="sudo mv ~/${f##*/} /var/www/mihaicosma.com/posts/"
        done
    fi

    # Keep Shaarli's generated navigation and header theme in sync.
    ./deploy_shaarli_theme.sh
fi
