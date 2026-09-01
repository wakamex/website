import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import build_blog as builder


class BlogBuildTests(unittest.TestCase):
    def parse(self, body):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "2026-08-21-demo.md"
            path.write_text(f"# Demo\n\n{body}\n")
            return builder.parse_post(path)

    def test_asciinema_shortcode_adds_player(self):
        date, _, title, body = self.parse('{{ asciinema("/demo.cast") }}')
        rendered = builder.render_post(date, "demo", title, body)

        self.assertIn('<div data-asciinema="/demo.cast"></div>', rendered)
        self.assertIn(f"asciinema-player@{builder.ASCIINEMA_PLAYER_VERSION}", rendered)
        self.assertIn("AsciinemaPlayer.create", rendered)

    def test_post_without_asciinema_omits_player_assets(self):
        date, _, title, body = self.parse("Plain post.")
        rendered = builder.render_post(date, "demo", title, body)

        self.assertNotIn("asciinema-player@", rendered)
        self.assertNotIn("AsciinemaPlayer.create", rendered)

    def test_multiple_demos_share_one_player_bundle(self):
        date, _, title, body = self.parse(
            '{{ asciinema("/first.cast") }}\n\n{{ asciinema("/second.cast") }}'
        )
        rendered = builder.render_post(date, "demo", title, body)

        self.assertIn('data-asciinema="/first.cast"', rendered)
        self.assertIn('data-asciinema="/second.cast"', rendered)
        self.assertEqual(rendered.count("asciinema-player.min.js"), 1)

    def test_malformed_asciinema_shortcode_fails(self):
        with self.assertRaisesRegex(ValueError, "invalid asciinema shortcode"):
            self.parse("{{ asciinema(/demo.cast) }}")

    def test_heading_ids_support_intra_post_links(self):
        _, _, _, body = self.parse(
            "See the [effective rate](#effective_rate).\n\n## Effective rate"
        )

        self.assertIn('<a href="#effective_rate">effective rate</a>', body)
        self.assertIn('<h2 id="effective_rate">Effective rate</h2>', body)

    def test_post_has_absolute_canonical_url(self):
        date, slug, title, body = self.parse("Plain post.")
        rendered = builder.render_post(date, slug, title, body)

        self.assertIn(
            '<link rel="canonical" href="https://mihaicosma.com/blog/demo.html">',
            rendered,
        )

    def test_build_writes_canonical_index_and_legacy_redirect(self):
        original_root = builder.ROOT
        original_blog_repo = builder.BLOG_REPO
        original_blog_output_dir = builder.BLOG_OUTPUT_DIR
        with tempfile.TemporaryDirectory() as directory:
            try:
                builder.ROOT = Path(directory)
                builder.BLOG_REPO = builder.ROOT / "source"
                builder.BLOG_OUTPUT_DIR = builder.ROOT / "blog"
                builder.BLOG_REPO.mkdir()
                subprocess.run(
                    ["git", "init", "-q", str(builder.BLOG_REPO)], check=True
                )
                subprocess.run(
                    ["git", "-C", str(builder.BLOG_REPO), "config", "user.name", "Test"],
                    check=True,
                )
                subprocess.run(
                    [
                        "git",
                        "-C",
                        str(builder.BLOG_REPO),
                        "config",
                        "user.email",
                        "test@example.com",
                    ],
                    check=True,
                )
                source = builder.BLOG_REPO / "2026-08-21-demo.md"
                source.write_text("# Committed title\n")
                subprocess.run(
                    ["git", "-C", str(builder.BLOG_REPO), "add", source.name],
                    check=True,
                )
                subprocess.run(
                    ["git", "-C", str(builder.BLOG_REPO), "commit", "-qm", "Initial"],
                    check=True,
                )
                source.write_text("# Uncommitted edit\n")
                draft = builder.BLOG_REPO / "2026-08-22-draft.md"
                draft.write_text("# Staged draft\n")
                subprocess.run(
                    ["git", "-C", str(builder.BLOG_REPO), "add", draft.name],
                    check=True,
                )
                (builder.BLOG_REPO / "2026-08-23-scratch.md").write_text(
                    "# Untracked draft\n"
                )
                builder.BLOG_OUTPUT_DIR.mkdir()
                (builder.BLOG_OUTPUT_DIR / "stale.html").write_text("stale")

                with mock.patch("builtins.print") as print_mock:
                    builder.main()
                print_mock.assert_called_once_with("checked 1 post(s), wrote 3 file(s)")

                index = (builder.BLOG_OUTPUT_DIR / "index.html").read_text()
                redirect = (builder.ROOT / "blog.html").read_text()
                rendered = (builder.BLOG_OUTPUT_DIR / "demo.html").read_text()
                self.assertIn('href="/blog/demo.html"', index)
                self.assertIn("Committed title", rendered)
                self.assertNotIn("Uncommitted edit", rendered)
                self.assertNotIn("Staged draft", index)
                self.assertNotIn("Untracked draft", index)
                self.assertFalse((builder.BLOG_OUTPUT_DIR / "stale.html").exists())
                self.assertIn('rel="canonical" href="/blog/"', redirect)
                self.assertIn('content="0; url=/blog/"', redirect)

                outputs = [
                    builder.BLOG_OUTPUT_DIR / "demo.html",
                    builder.BLOG_OUTPUT_DIR / "index.html",
                    builder.ROOT / "blog.html",
                ]
                preserved_mtime = 1_000_000_000
                for output in outputs:
                    os.utime(output, ns=(preserved_mtime, preserved_mtime))

                with mock.patch("builtins.print") as print_mock:
                    builder.main()
                print_mock.assert_called_once_with("checked 1 post(s), wrote 0 file(s)")

                for output in outputs:
                    self.assertEqual(preserved_mtime, output.stat().st_mtime_ns)
            finally:
                builder.ROOT = original_root
                builder.BLOG_REPO = original_blog_repo
                builder.BLOG_OUTPUT_DIR = original_blog_output_dir


if __name__ == "__main__":
    unittest.main()
