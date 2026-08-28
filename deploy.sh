#!/bin/bash
set -e
cd "$(dirname "$0")"

build_started_at=$(date +%s.%N)

echo "Building shared navigation and themes..."
python3 build_shared_site.py

echo "Building blog..."
python3 build_blog.py

echo "Building Autoresearch pages..."
python3 build_autoresearch.py --require-fresh

build_finished_at=$(date +%s.%N)
build_elapsed=$(awk -v start="$build_started_at" -v finish="$build_finished_at" 'BEGIN { printf "%.2f", finish - start }')
echo "Built in $build_elapsed seconds"

# Top-level files: default set, or whatever the user passed.
files="${@:-index.html autoresearch.html projects.html style.css resume.html status.html blog.html og-image.png meters.js site-nav.js D2CodingLigature-web.woff2 youtube-cli-uploader-demo.cast}"
echo "Uploading top-level site files..."
gcloud compute scp $files mc-new:~ --zone=us-central1-a

echo "Installing top-level site files on the server..."
for f in $files; do
    gcloud compute ssh mc-new --zone=us-central1-a --command="sudo mv ~/${f##*/} /var/www/mihaicosma.com/"
done

# Blog HTML: only sync when running the default deploy (no args).
if [ $# -eq 0 ]; then
    blog_files=(blog/*.html)
    if [ -e "${blog_files[0]}" ]; then
        echo "Uploading ${#blog_files[@]} generated blog post(s)..."
        gcloud compute ssh mc-new --zone=us-central1-a --command="sudo mkdir -p /var/www/mihaicosma.com/blog"
        gcloud compute scp "${blog_files[@]}" mc-new:~ --zone=us-central1-a

        echo "Installing generated blog posts on the server..."
        for f in "${blog_files[@]}"; do
            gcloud compute ssh mc-new --zone=us-central1-a --command="sudo mv ~/${f##*/} /var/www/mihaicosma.com/blog/"
        done
    fi

    # Keep Shaarli's generated navigation and header theme in sync.
    echo "Deploying the Shaarli navigation and theme..."
    ./deploy_shaarli_theme.sh
fi
