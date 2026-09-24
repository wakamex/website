#!/bin/bash
set -e
cd "$(dirname "$0")"

parsync_bin=/code/parsync-local-to-remote/target/release/parsync
remote_root=mc:/var/www/mihaicosma.com
shaarli_stamp=.private/shaarli-deploy.hash
inquisition_source=/code/inquisition/prototype/chapter3.html

force_shaarli=false
include_inquisition=false
requested_files=()
for arg in "$@"; do
    case "$arg" in
        --force-shaarli)
            force_shaarli=true
            ;;
        --inquisition)
            include_inquisition=true
            ;;
        *)
            requested_files+=("$arg")
            ;;
    esac
done

inquisition_only=false
if $include_inquisition && [ ${#requested_files[@]} -eq 0 ] && ! $force_shaarli; then
    inquisition_only=true
fi

if [ ${#requested_files[@]} -eq 0 ] && ! $include_inquisition; then
    default_deploy=true
else
    default_deploy=false
fi

if [ ! -x "$parsync_bin" ]; then
    echo "Missing executable parsync branch build: $parsync_bin" >&2
    exit 1
fi

if ! $inquisition_only; then
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
fi

# Top-level files: default set, or whatever the user passed.
default_files=(.htaccess index.html autoresearch.html projects.html style.css resume.html status.html blog.html og-image.png meters.js site-nav.js D2CodingLigature-web.woff2 youtube-cli-uploader-demo.cast)
if $default_deploy; then
    files=("${default_files[@]}")
else
    files=("${requested_files[@]}")
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
    if [ -d "$deploy_stage/inquisition" ]; then
        rmdir "$deploy_stage/inquisition"
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
if $default_deploy; then
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

# Trusted mapping from the Inquisition workspace to its stable public URL.
if $default_deploy || $include_inquisition; then
    if [ ! -f "$inquisition_source" ] || [ -L "$inquisition_source" ]; then
        echo "Inquisition artifact must be a regular, non-symlink file: $inquisition_source" >&2
        exit 1
    fi
    python3 - "$inquisition_source" <<'PY'
import sys
from pathlib import Path

path = Path(sys.argv[1])
try:
    content = path.read_text(encoding="utf-8")
except UnicodeDecodeError as error:
    raise SystemExit(f"Inquisition artifact is not valid UTF-8: {error}")
normalized = content.lstrip("\ufeff \t\r\n").lower()
if (
    not normalized.startswith("<!doctype html")
    or "<html" not in normalized
    or "</html>" not in normalized
):
    raise SystemExit("Inquisition artifact must be a complete HTML document")
PY
    mkdir "$deploy_stage/inquisition"
    staged_file="$deploy_stage/inquisition/index.html"
    cp -p -- "$inquisition_source" "$staged_file"
    staged_files+=("$staged_file")
fi

upload_started_at=$(date +%s.%N)

echo "Uploading ${#staged_files[@]} site files..."
"$parsync_bin" -rP --verify-existing "$deploy_stage/*" "$remote_root"

upload_finished_at=$(date +%s.%N)
upload_elapsed=$(awk -v start="$upload_started_at" -v finish="$upload_finished_at" 'BEGIN { printf "%.2f", finish - start }')
echo "Uploads completed in $upload_elapsed seconds"

cleanup_stage
trap - EXIT

if $default_deploy || $force_shaarli; then
    shaarli_inputs=(
        deploy_shaarli_theme.sh
        shaarli-theme/refined.css
        shaarli-theme/patch_linklist.py
        shaarli-theme/build_css_bundle.py
        shaarli-theme/inline_svg_icons.py
        shaarli-theme/site_navigation/site_navigation.php
        shaarli-theme/site_navigation/site_navigation.meta
        shaarli-theme/site_navigation/navigation.generated.php
    )
    for file in "${shaarli_inputs[@]}"; do
        if [ ! -f "$file" ]; then
            echo "Shaarli deployment input not found: $file" >&2
            exit 1
        fi
    done
    shaarli_hash=$(sha256sum -- "${shaarli_inputs[@]}" | sha256sum | awk '{print $1}')
    deployed_shaarli_hash=
    if [ -f "$shaarli_stamp" ]; then
        deployed_shaarli_hash=$(<"$shaarli_stamp")
    fi

    if ! $force_shaarli && [ "$shaarli_hash" = "$deployed_shaarli_hash" ]; then
        echo "Shaarli inputs unchanged; skipping theme deployment"
    else
        # Keep Shaarli's generated navigation and header theme in sync.
        echo "Deploying the Shaarli navigation and theme..."
        ./deploy_shaarli_theme.sh
        mkdir -p "${shaarli_stamp%/*}"
        stamp_tmp=$(mktemp "${shaarli_stamp}.XXXXXX")
        printf '%s\n' "$shaarli_hash" > "$stamp_tmp"
        mv -- "$stamp_tmp" "$shaarli_stamp"
    fi
fi
