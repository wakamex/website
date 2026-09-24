# Website deployment

`./deploy.sh` rebuilds and publishes the normal static site, Blog, Autoresearch, declared external artifacts, and changed Shaarli inputs.

Passing website-relative filenames publishes only those top-level files. `--force-shaarli` also runs the Shaarli deployment regardless of its input hash.

## Inquisition prototype contract

The canonical public artifact root is `/code/inquisition/prototype/`. The website repository does not contain a copy. `index.html` is required and becomes the page at `/inquisition/`; every other file and subdirectory keeps its path below that URL.

Every path under `prototype/` is public. Keep drafts, source material, credentials, and internal notes elsewhere. The deployer rejects hidden paths, symlinks, special files, invalid UTF-8 HTML, and incomplete HTML documents.

A normal `./deploy.sh` includes the current artifact. Use `./deploy.sh --inquisition` to publish only the prototype at `https://mihaicosma.com/inquisition/`. The upload uses a remote staging directory and swaps the completed tree into place, so removed source files also disappear from the public tree without exposing a partial deployment.

Run `./watch_inquisition.sh` to publish once immediately and then republish after the prototype tree has been quiet for five seconds. Pass another positive integer to change the idle interval, such as `./watch_inquisition.sh 10`. Validation or upload failures leave the prior live tree in place and the watcher continues waiting for another source change.
