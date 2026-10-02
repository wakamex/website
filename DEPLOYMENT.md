# Website deployment

`./deploy.sh` rebuilds and publishes the normal static site, Blog, Autoresearch, declared external artifacts, and changed Shaarli inputs.

A default deploy also publishes the Sycophancy Bench v2 page from `/code/sycophant-public/v2/index.html` at `https://mihaicosma.com/sycophancy/`.

A default deploy ends by naming the top-level files it skipped because they are in neither `default_files` nor `private_files` in `deploy.sh`, leaving out scripts, Markdown, and Apache config. Add a new public page to `default_files`, or a file that should stay off the server to `private_files`.

Passing website-relative filenames publishes only those top-level files. `--force-shaarli` also runs the Shaarli deployment regardless of its input hash.

## Inquisition prototype contract

The canonical public artifact root is `/code/inquisition/prototype/`. The website repository does not contain a copy. `index.html` or `index.md` is required and becomes the page at `/inquisition/`; every other file and subdirectory keeps its path below that URL.

Markdown files are rendered recursively during staging with the same fenced-code, table, and heading-anchor support as the Blog. `notes.md` becomes `notes.html`, and the raw Markdown is not published. An HTML file and Markdown file cannot produce the same output path.

Every path under `prototype/` is public. Keep drafts, source material, credentials, and internal notes elsewhere. The deployer rejects hidden paths, symlinks, special files, invalid UTF-8 HTML, and incomplete HTML documents.

A normal `./deploy.sh` includes the current artifact. Use `./deploy.sh --inquisition` to publish only the prototype at `https://mihaicosma.com/inquisition/`. Website uploads use eight parsync workers, staying below the server's SSH startup limit. The deploy first deletes live files that no longer exist in the source, then uploads directly into the live tree, where parsync skips unchanged files. While an upload runs, visitors can briefly see a mix of old and new files. Apache sends `Cache-Control: no-cache` for the entire URL tree, requiring clients to revalidate cached files while still allowing `304 Not Modified` responses.

Run `./watch_inquisition.sh` to publish once immediately and then republish after the prototype tree has been quiet for five seconds. Pass another positive integer to change the idle interval, such as `./watch_inquisition.sh 10`. The persistent file monitor queues changes made during an upload, and a source-tree fingerprint before and after every publish independently forces a catch-up after the tree becomes quiet. Files matching `*.tmp.*` do not trigger or delay a publish; moving one onto its final filename does. A validation failure leaves the live tree untouched; an upload failure can leave it partly updated. Both retry after 30 seconds.
