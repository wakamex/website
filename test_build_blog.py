import tempfile
import unittest
from pathlib import Path

import build_blog as builder


class BlogBuildTests(unittest.TestCase):
    def parse(self, body):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "2026-08-21-demo.md"
            path.write_text(f"# Demo\n\n{body}\n")
            return builder.parse_post(path)

    def test_asciinema_shortcode_adds_player(self):
        date, _, title, body = self.parse('{{ asciinema("/demo.cast") }}')
        rendered = builder.render_post(date, title, body)

        self.assertIn('<div data-asciinema="/demo.cast"></div>', rendered)
        self.assertIn(f"asciinema-player@{builder.ASCIINEMA_PLAYER_VERSION}", rendered)
        self.assertIn("AsciinemaPlayer.create", rendered)

    def test_post_without_asciinema_omits_player_assets(self):
        date, _, title, body = self.parse("Plain post.")
        rendered = builder.render_post(date, title, body)

        self.assertNotIn("asciinema-player@", rendered)
        self.assertNotIn("AsciinemaPlayer.create", rendered)

    def test_multiple_demos_share_one_player_bundle(self):
        date, _, title, body = self.parse(
            '{{ asciinema("/first.cast") }}\n\n{{ asciinema("/second.cast") }}'
        )
        rendered = builder.render_post(date, title, body)

        self.assertIn('data-asciinema="/first.cast"', rendered)
        self.assertIn('data-asciinema="/second.cast"', rendered)
        self.assertEqual(rendered.count("asciinema-player.min.js"), 1)

    def test_malformed_asciinema_shortcode_fails(self):
        with self.assertRaisesRegex(ValueError, "invalid asciinema shortcode"):
            self.parse("{{ asciinema(/demo.cast) }}")


if __name__ == "__main__":
    unittest.main()
