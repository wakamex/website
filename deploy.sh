#!/bin/bash
set -e
cd "$(dirname "$0")"

parsync_bin=/code/parsync-local-to-remote/target/release/parsync
parsync_jobs=8
remote_host=mc
remote_webroot=/var/www/mihaicosma.com
remote_root=$remote_host:$remote_webroot
shaarli_stamp=.private/shaarli-deploy.hash
inquisition_source=/code/inquisition/prototype
sycophancy_source=/code/sycophant-public/v2/index.html
inquisition_remote_work=$remote_webroot/.inquisition-deploy
inquisition_remote_stage=$inquisition_remote_work/stage
inquisition_remote_target=$remote_webroot/inquisition
inquisition_remote_backup=$inquisition_remote_work/previous

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
default_files=(.htaccess index.html autoresearch.html projects.html style.css resume.html status.html blog.html og-image.png meters.js site-nav.js ClankerMono-web.woff2 gpu-sales.html gpu-sales-data.js youtube-cli-uploader-demo.cast)
if $default_deploy; then
    files=("${default_files[@]}")
else
    files=("${requested_files[@]}")
fi

deploy_stage=$(mktemp -d)
inquisition_stage=
staged_files=()
cleanup_stage() {
    for staged_file in "${staged_files[@]}"; do
        [ -e "$staged_file" ] || continue
        unlink "$staged_file"
    done
    for staged_dir in blog sycophancy; do
        if [ -d "$deploy_stage/$staged_dir" ]; then
            rmdir "$deploy_stage/$staged_dir"
        fi
    done
    rmdir "$deploy_stage"
    if [ -n "$inquisition_stage" ] && [ -d "$inquisition_stage" ]; then
        rm -rf -- "$inquisition_stage"
    fi
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

# Sycophancy Bench v2 results page, a self-contained file from the public sycophant repository.
if $default_deploy; then
    if [ ! -f "$sycophancy_source" ]; then
        echo "Sycophancy page not found: $sycophancy_source" >&2
        exit 1
    fi
    mkdir "$deploy_stage/sycophancy"
    staged_file="$deploy_stage/sycophancy/index.html"
    cp -p -- "$sycophancy_source" "$staged_file"
    staged_files+=("$staged_file")
    staged_file="$deploy_stage/sycophancy/og.png"
    cp -p -- "${sycophancy_source%/*}/og.png" "$staged_file"
    staged_files+=("$staged_file")
fi

# Trusted mapping from the Inquisition workspace to its stable public URL.
if $default_deploy || $include_inquisition; then
    inquisition_stage=$(mktemp -d)
    /usr/bin/python3 build_inquisition.py "$inquisition_source" "$inquisition_stage"
fi

if [ ${#staged_files[@]} -gt 0 ]; then
    upload_started_at=$(date +%s.%N)

    echo "Uploading ${#staged_files[@]} site files..."
    "$parsync_bin" -rP --jobs "$parsync_jobs" --verify-existing \
        "$deploy_stage/*" "$remote_root"

    upload_finished_at=$(date +%s.%N)
    upload_elapsed=$(awk -v start="$upload_started_at" -v finish="$upload_finished_at" 'BEGIN { printf "%.2f", finish - start }')
    echo "Uploads completed in $upload_elapsed seconds"
fi

if [ -n "$inquisition_stage" ]; then
    inquisition_file_count=$(find "$inquisition_stage" -type f | wc -l)
    echo "Uploading $inquisition_file_count Inquisition prototype file(s)..."
    ssh "$remote_host" "
        set -e
        test ! -L '$inquisition_remote_work'
        test ! -L '$inquisition_remote_stage'
        test ! -L '$inquisition_remote_backup'
        install -d -m 700 '$inquisition_remote_work'
        rm -rf -- '$inquisition_remote_stage' '$inquisition_remote_backup'
        mkdir -- '$inquisition_remote_stage'
    "
    if ! "$parsync_bin" -rP --jobs "$parsync_jobs" --verify-existing \
        "$inquisition_stage/*" \
        "$remote_host:$inquisition_remote_stage"; then
        ssh "$remote_host" "
            rm -rf -- '$inquisition_remote_stage'
            rmdir -- '$inquisition_remote_work' 2>/dev/null || true
        " || true
        exit 1
    fi
    ssh "$remote_host" "
        set -e
        test ! -L '$inquisition_remote_target'
        chmod 2755 '$inquisition_remote_stage'
        if [ -e '$inquisition_remote_target' ]; then
            mv -- '$inquisition_remote_target' '$inquisition_remote_backup'
        fi
        if mv -- '$inquisition_remote_stage' '$inquisition_remote_target'; then
            rm -rf -- '$inquisition_remote_backup'
            rmdir -- '$inquisition_remote_work'
        else
            if [ -e '$inquisition_remote_backup' ]; then
                mv -- '$inquisition_remote_backup' '$inquisition_remote_target'
            fi
            exit 1
        fi
    "
    echo "Inquisition prototype deployed"
fi

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
