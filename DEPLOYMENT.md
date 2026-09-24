# Website deployment

`./deploy.sh` rebuilds and publishes the normal static site, Blog, Autoresearch, declared external artifacts, and changed Shaarli inputs.

Passing website-relative filenames publishes only those top-level files. `--force-shaarli` also runs the Shaarli deployment regardless of its input hash.

## Inquisition prototype contract

The canonical source is `/code/inquisition/prototype/chapter3.html`. The website repository does not contain a copy. During staging, `deploy.sh` validates that the source is a regular non-symlink file containing one complete UTF-8 HTML document, then maps it to `inquisition/index.html`.

A normal `./deploy.sh` includes the current artifact. Use `./deploy.sh --inquisition` to publish only the prototype at `https://mihaicosma.com/inquisition/`.
