#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "Building shared navigation and themes..."
python3 build_shared_site.py

echo "Building blog..."
python3 build_blog.py

echo "Building Autoresearch pages..."
python3 build_autoresearch.py --require-fresh

# Top-level files: default set, or whatever the user passed.
files="${@:-index.html autoresearch.html projects.html style.css resume.html status.html blog.html og-image.png meters.js site-nav.js D2CodingLigature-web.woff2}"
echo "Uploading top-level site files..."
gcloud compute scp $files mc-new:~ --zone=us-central1-a

echo "Installing top-level site files on the server..."
for f in $files; do
    gcloud compute ssh mc-new --zone=us-central1-a --command="sudo mv ~/${f##*/} /var/www/mihaicosma.com/"
done

# Post HTML: only sync when running the default deploy (no args).
if [ $# -eq 0 ]; then
    post_files=(posts/*.html)
    if [ -e "${post_files[0]}" ]; then
        echo "Uploading ${#post_files[@]} generated blog post(s)..."
        gcloud compute ssh mc-new --zone=us-central1-a --command="sudo mkdir -p /var/www/mihaicosma.com/posts"
        gcloud compute scp "${post_files[@]}" mc-new:~ --zone=us-central1-a

        echo "Installing generated blog posts on the server..."
        for f in "${post_files[@]}"; do
            gcloud compute ssh mc-new --zone=us-central1-a --command="sudo mv ~/${f##*/} /var/www/mihaicosma.com/posts/"
        done
    fi

    # Keep Shaarli's generated navigation and header theme in sync.
    echo "Deploying the Shaarli navigation and theme..."
    ./deploy_shaarli_theme.sh
fi
