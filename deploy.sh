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
inquisition_remote_target=$remote_webroot/inquisition

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
default_files=(.htaccess index.html autoresearch.html projects.html style.css resume.html status.html blog.html og-image.png meters.js site-nav.js ClankerMono-web.woff2 gpu-sales.html gpu-sales-data.js burn-widgets.html youtube-cli-uploader-demo.cast)
# Top-level files that stay off the server: build inputs, the GPU scraper's raw data, and the desktop font.
private_files=(site-navigation.json site-theme.css gpu-sales-source.json ClankerMono-NF.ttf)
if $default_deploy; then
    files=("${default_files[@]}")
else
    files=("${requested_files[@]}")
fi

deploy_stage=$(mktemp -d)
cleanup_stage() {
    rm -rf -- "$deploy_stage"
}
trap cleanup_stage EXIT

for file in "${files[@]}"; do
    if [ ! -f "$file" ]; then
        echo "Top-level deployment file not found: $file" >&2
        exit 1
    fi
    cp -p -- "$file" "$deploy_stage/${file##*/}"
done

# Blog HTML and preview images: only include when running the default deploy (no args).
if $default_deploy; then
    blog_files=(blog/*.html)
    blog_images=(blog/*.png)
    [ -e "${blog_images[0]}" ] && blog_files+=("${blog_images[@]}")
    if [ -e "${blog_files[0]}" ]; then
        mkdir "$deploy_stage/blog"
        cp -p -- "${blog_files[@]}" "$deploy_stage/blog/"
    fi
fi

# Sycophancy Bench v2 results page, a self-contained file from the public sycophant repository.
if $default_deploy; then
    if [ ! -f "$sycophancy_source" ]; then
        echo "Sycophancy page not found: $sycophancy_source" >&2
        exit 1
    fi
    mkdir "$deploy_stage/sycophancy"
    cp -p -- "$sycophancy_source" "${sycophancy_source%/*}/og.png" "$deploy_stage/sycophancy/"
fi

# Trusted mapping from the Inquisition workspace to its stable public URL.
if $default_deploy || $include_inquisition; then
    /usr/bin/python3 build_inquisition.py "$inquisition_source" "$deploy_stage/inquisition"
    # parsync never deletes, so first remove live entries that are absent locally or have changed type.
    (cd "$deploy_stage/inquisition" && find . -mindepth 1 -printf '%y %p\0') | ssh "$remote_host" "bash -c '
        set -eo pipefail
        test ! -L $inquisition_remote_target
        [ -d $inquisition_remote_target ] || exit 0
        cd $inquisition_remote_target
        comm -z -13 <(sort -z) <(find . -mindepth 1 -printf \"%y %p\\0\" | sort -z) \
            | cut -z -d \" \" -f 2- | xargs -0 -r rm -rf --
    '"
fi

staged_count=$(find "$deploy_stage" -type f | wc -l)
if [ "$staged_count" -gt 0 ]; then
    upload_started_at=$(date +%s.%N)

    echo "Syncing $staged_count site file(s)..."
    "$parsync_bin" -rP --jobs "$parsync_jobs" "$deploy_stage/*" "$remote_root"

    upload_finished_at=$(date +%s.%N)
    upload_elapsed=$(awk -v start="$upload_started_at" -v finish="$upload_finished_at" 'BEGIN { printf "%.2f", finish - start }')
    echo "Sync completed in $upload_elapsed seconds"
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

if $default_deploy; then
    # Name top-level files that a default deploy skips, so new pages are not silently left off the list.
    skipped_files=()
    while IFS= read -r file; do
        case " ${default_files[*]} ${private_files[*]} " in
            *" $file "*) continue ;;
        esac
        case "$file" in
            */* | .gitignore | *.py | *.sh | *.md | *.conf) continue ;;
        esac
        skipped_files+=("$file")
    done < <(git ls-files --cached --others --exclude-standard | sort -u)
    if [ ${#skipped_files[@]} -gt 0 ]; then
        echo "Not deployed (not in default_files or private_files): ${skipped_files[*]}"
    fi
fi
