# Public prototype artifact

Treat `/code/inquisition/prototype/` as the complete public artifact for browser testing. The trusted website deployment mirrors this directory to `https://mihaicosma.com/inquisition/`; do not write into `/code/website` or run its deployment commands.

`prototype/index.html` is required and is the entry page. Every other file and subdirectory keeps the same relative public path, so use relative links such as `styles.css`, `scripts/game.js`, and `images/map.webp`.

Everything under `prototype/` is public. Keep drafts, notes, source material, credentials, logs, and temporary files elsewhere. Do not create hidden paths, symlinks, sockets, named pipes, or other special files in the public artifact tree.

Every `.html` file must be a complete UTF-8 HTML document with a doctype, opening `<html>` element, and closing `</html>` element. Page titles, chapter numbers, and visible labels come directly from the HTML; deployment does not infer or rewrite them from filenames.

The public directory is an exact mirror. Delete obsolete public files from `prototype/` when they should disappear from the site. A watcher may publish after five quiet seconds, so leave the directory in a coherent, valid state when a change batch is complete. Failed validation leaves the previous live version untouched.
