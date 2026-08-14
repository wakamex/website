#!/usr/bin/env python3

from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import PurePosixPath
from urllib.parse import unquote, urlsplit


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.is_blocked():
            self.send_error(404)
            return
        super().do_GET()

    def do_HEAD(self):
        if self.is_blocked():
            self.send_error(404)
            return
        super().do_HEAD()

    def is_blocked(self):
        path = unquote(urlsplit(self.path).path)
        return any(part.startswith(".") for part in PurePosixPath(path).parts)

    def list_directory(self, path):
        self.send_error(404)
        return None


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Serve the site on the home LAN")
    parser.add_argument("port", type=int)
    args = parser.parse_args()

    ThreadingHTTPServer(("0.0.0.0", args.port), Handler).serve_forever()
