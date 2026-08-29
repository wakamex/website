#!/bin/bash
set -e
cd "$(dirname "$0")"

parsync_bin=/code/parsync-local-to-remote/target/release/parsync
remote_root=mc:/var/www/mihaicosma.com

if [ ! -x "$parsync_bin" ]; then
    echo "Missing executable parsync branch build: $parsync_bin" >&2
    exit 1
fi

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
default_files=(index.html autoresearch.html projects.html style.css resume.html status.html blog.html og-image.png meters.js site-nav.js D2CodingLigature-web.woff2 youtube-cli-uploader-demo.cast)
if [ $# -eq 0 ]; then
    files=("${default_files[@]}")
else
    files=("$@")
fi

deploy_stage=$(mktemp -d)
cleanup_stage() {
    for staged_file in "$deploy_stage"/*; do
        [ -e "$staged_file" ] || continue
        unlink "$staged_file"
    done
    rmdir "$deploy_stage"
}
trap cleanup_stage EXIT

for file in "${files[@]}"; do
    if [ ! -f "$file" ]; then
        echo "Top-level deployment file not found: $file" >&2
        exit 1
    fi
    cp -p -- "$file" "$deploy_stage/${file##*/}"
done

upload_started_at=$(date +%s.%N)

echo "Uploading top-level site files..."
"$parsync_bin" -rP --verify-existing "$deploy_stage/*" "$remote_root"
cleanup_stage
trap - EXIT

# Blog HTML: only sync when running the default deploy (no args).
if [ $# -eq 0 ]; then
    blog_files=(blog/*.html)
    if [ -e "${blog_files[0]}" ]; then
        echo "Uploading ${#blog_files[@]} generated blog post(s)..."
        "$parsync_bin" -rP --verify-existing "$PWD/blog/*" "$remote_root/blog"
    fi
fi

upload_finished_at=$(date +%s.%N)
upload_elapsed=$(awk -v start="$upload_started_at" -v finish="$upload_finished_at" 'BEGIN { printf "%.2f", finish - start }')
echo "Uploads completed in $upload_elapsed seconds"

if [ $# -eq 0 ]; then
    # Keep Shaarli's generated navigation and header theme in sync.
    echo "Deploying the Shaarli navigation and theme..."
    ./deploy_shaarli_theme.sh
fi
