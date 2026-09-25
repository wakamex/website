# Public prototype artifact

Treat `/code/inquisition/prototype/` as the complete public artifact for browser testing. The trusted website deployment mirrors this directory to `https://mihaicosma.com/inquisition/`; do not write into `/code/website` or run its deployment commands.

`prototype/index.html` or `prototype/index.md` is required and is the entry page. Every other file and subdirectory keeps the same relative public path, so use relative links such as `styles.css`, `scripts/game.js`, and `images/map.webp`.

Markdown files are rendered recursively during deployment. `notes.md` becomes `notes.html`, and the raw `.md` file is not published. Markdown supports fenced code blocks, tables, and linkable heading IDs like the site Blog. Rendered Markdown uses the site's typography without its navigation or meters gadget. Start every Markdown file with `# Title`, link to rendered pages with their `.html` paths, and do not create both `name.md` and `name.html` because they target the same public URL.

Everything under `prototype/` is public. Keep drafts, notes, source material, credentials, logs, and temporary files elsewhere. Do not create hidden paths, symlinks, sockets, named pipes, or other special files in the public artifact tree.

Every `.html` file must be a complete UTF-8 HTML document with a doctype, opening `<html>` element, and closing `</html>` element. Page titles, chapter numbers, and visible labels come directly from the HTML; deployment does not infer or rewrite them from filenames.

The public directory is an exact mirror. Delete obsolete public files from `prototype/` when they should disappear from the site. A watcher may publish after five quiet seconds, so leave the directory in a coherent, valid state when a change batch is complete. Changes made during an upload queue a catch-up publish. Files matching `*.tmp.*` are ignored until they are moved onto a final filename. Failed validation or upload leaves the previous live version untouched and retries after 30 seconds.
