#!/usr/bin/env python3
"""Generate static-site and Shaarli outputs from shared sources."""

from site_shared import (
    NAVIGATION_END,
    ROOT,
    THEME_END,
    THEME_START,
    SharedSiteError,
    render_shaarli_navigation,
    render_site_header,
    render_theme,
    replace_generated_block,
    write_if_changed,
)


STATIC_PAGES = {
    ROOT / "index.html": ("home", ("github", "twitter", "resume")),
    ROOT / "resume.html": ("resume", ()),
}
THEME_OUTPUTS = {
    ROOT / "style.css": "static",
    ROOT / "shaarli-theme" / "refined.css": "shaarli",
}


def update_static_navigation(path, active, secondary_slugs):
    content = path.read_text(encoding="utf-8")
    start = f"<!-- GENERATED SITE NAVIGATION:START active={active} -->"
    generated = render_site_header(active, secondary_slugs)
    inner = generated.removeprefix(start + "\n").removesuffix("\n" + NAVIGATION_END)
    write_if_changed(
        path,
        replace_generated_block(content, start, NAVIGATION_END, inner),
    )


def main():
    for path, (active, secondary_slugs) in STATIC_PAGES.items():
        update_static_navigation(path, active, secondary_slugs)

    for path, target in THEME_OUTPUTS.items():
        content = path.read_text(encoding="utf-8")
        write_if_changed(
            path,
            replace_generated_block(
                content, THEME_START, THEME_END, render_theme(target)
            ),
        )

    write_if_changed(
        ROOT / "shaarli-theme" / "site_navigation" / "navigation.generated.php",
        render_shaarli_navigation(),
    )
    print("built shared navigation and header themes")


if __name__ == "__main__":
    try:
        main()
    except SharedSiteError as error:
        raise SystemExit(str(error)) from error
