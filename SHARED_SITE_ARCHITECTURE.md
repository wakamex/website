# Shared site navigation and header theme

## Decision

The main site and Shaarli use one canonical navigation source and one canonical header-theme source, with separate generated outputs for each application.

This is intentionally a build-time design. Do not replace it with JavaScript-rendered navigation, server-side includes, or a CSS `@import`. Those approaches add runtime dependencies and can reintroduce loading flashes.

The current level of reuse is the intended stopping point. It addresses demonstrated navigation and visual drift without coupling unrelated parts of the main site and Shaarli.

## Canonical sources

- `site-navigation.json` contains navigation labels, URLs, slugs, and order.
- `site-theme.css` contains the shared header design and target-specific static-site and Shaarli rules.
- `site_shared.py` renders the static header, Shaarli PHP navigation, and target-specific CSS.
- `build_shared_site.py` writes the generated outputs.

Generated HTML and CSS blocks are marked as generated and should not be edited directly.

## Workflow

1. Edit `site-navigation.json` to add, remove, rename, or reorder a navigation item.
2. Edit `site-theme.css` to change the shared header appearance.
3. Run `python3 build_shared_site.py` to inspect generated changes locally.
4. Run `./deploy.sh` for a full deployment. It updates both the static site and Shaarli.

The normal deployment also rebuilds Blog and Autoresearch. Shaarli PHP files are syntax-checked on the server before installation.

## What is already centralized

- Navigation labels, URLs, slugs, and order.
- Header colors, borders, dimensions, link states, and active-state treatment.
- Static and Shaarli active-page generation.
- Static and Shaarli deployment through the full deployment path.
- Basic navigation-source validation and deterministic generation.
- A homepage-only secondary row for GitHub, Twitter, and Resume, generated from the same canonical navigation data.

## Deliberately separate concerns

- Shaarli's secondary actions remain Shaarli-specific.
- The static and Shaarli mobile-menu implementations remain separate because their markup and JavaScript differ.
- Their responsive breakpoints remain separate because the layouts have different space requirements.
- General content-link styling remains separate from navigation-link styling.
- Status and specialized dashboards keep their specialized layouts unless a future design decision changes that.

## Reuse ideas rejected for now

- Do not centralize the entire site palette. It would couple unrelated components and require broad CSS churn.
- Do not centralize all font declarations. The small amount of repetition is easier to understand than another generation layer.
- Do not centralize all link styling. Navigation, content, metadata, and application controls have different roles.
- Do not introduce a common Blog and Autoresearch page shell yet. Their small amount of remaining duplication does not justify another abstraction.
- Do not extract a shared deployment configuration or general build-utility library while only a few short scripts use those values and helpers.
- Do not add runtime JavaScript navigation or Apache includes. Static generated HTML is faster, locally previewable, and works without JavaScript.

## Possible future additions

Add destination-existence checks only if navigation changes become frequent enough for broken internal links to be a recurring problem.

Add a generated-output freshness check only when the repository gains CI or outside contributors. The current full deployment already regenerates outputs automatically.

Reconsider any rejected abstraction only after repeated maintenance errors demonstrate a concrete need. Avoid adding it solely to remove a few duplicated lines.
