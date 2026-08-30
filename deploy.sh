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
staged_files=()
cleanup_stage() {
    for staged_file in "${staged_files[@]}"; do
        [ -e "$staged_file" ] || continue
        unlink "$staged_file"
    done
    if [ -d "$deploy_stage/blog" ]; then
        rmdir "$deploy_stage/blog"
    fi
    rmdir "$deploy_stage"
}
trap cleanup_stage EXIT

for file in "${files[@]}"; do
    if [ ! -f "$file" ]; then
        echo "Top-level deployment file not found: $file" >&2
        exit 1
    fi
    staged_file="$deploy_stage/${file##*/}"
    cp -p -- "$file" "$staged_file"
    staged_files+=("$staged_file")
done

# Blog HTML: only include when running the default deploy (no args).
if [ $# -eq 0 ]; then
    blog_files=(blog/*.html)
    if [ -e "${blog_files[0]}" ]; then
        mkdir "$deploy_stage/blog"
        for file in "${blog_files[@]}"; do
            staged_file="$deploy_stage/blog/${file##*/}"
            cp -p -- "$file" "$staged_file"
            staged_files+=("$staged_file")
        done
    fi
fi

upload_started_at=$(date +%s.%N)

echo "Uploading ${#staged_files[@]} site files..."
"$parsync_bin" -rP --verify-existing "$deploy_stage/*" "$remote_root"

upload_finished_at=$(date +%s.%N)
upload_elapsed=$(awk -v start="$upload_started_at" -v finish="$upload_finished_at" 'BEGIN { printf "%.2f", finish - start }')
echo "Uploads completed in $upload_elapsed seconds"

cleanup_stage
trap - EXIT

if [ $# -eq 0 ]; then
    # Keep Shaarli's generated navigation and header theme in sync.
    echo "Deploying the Shaarli navigation and theme..."
    ./deploy_shaarli_theme.sh
fi
