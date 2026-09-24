import tempfile
import unittest
from pathlib import Path

import build_inquisition as builder


class InquisitionBuildTests(unittest.TestCase):
    def test_markdown_is_rendered_recursively_without_publishing_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            destination = root / "destination"
            (source / "notes").mkdir(parents=True)
            (source / "index.md").write_text(
                "# Prototype\n\nSee the [details](notes/details.html).\n",
                encoding="utf-8",
            )
            (source / "notes" / "details.md").write_text(
                "# Details\n\n## Evidence rate\n\n| A | B |\n| - | - |\n| 1 | 2 |\n",
                encoding="utf-8",
            )
            (source / "asset.txt").write_text("asset", encoding="utf-8")

            self.assertEqual(3, builder.build(source, destination))

            index = (destination / "index.html").read_text(encoding="utf-8")
            details = (destination / "notes" / "details.html").read_text(
                encoding="utf-8"
            )
            self.assertIn("<title>Prototype — Mihai Cosma</title>", index)
            self.assertIn('href="https://mihaicosma.com/inquisition/"', index)
            self.assertIn('<h2 id="evidence_rate">Evidence rate</h2>', details)
            self.assertIn("<table>", details)
            self.assertIn('<link rel="stylesheet" href="/style.css">', details)
            self.assertNotIn("site-header", details)
            self.assertNotIn("meters-link", details)
            self.assertNotIn("/meters.js", details)
            self.assertNotIn("/site-nav.js", details)
            self.assertEqual("asset", (destination / "asset.txt").read_text())
            self.assertFalse((destination / "index.md").exists())
            self.assertFalse((destination / "notes" / "details.md").exists())

    def test_existing_complete_html_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            destination = root / "destination"
            source.mkdir()
            document = "<!DOCTYPE html><html><body>Prototype</body></html>"
            (source / "index.html").write_text(document, encoding="utf-8")

            self.assertEqual(1, builder.build(source, destination))
            self.assertEqual(
                document, (destination / "index.html").read_text(encoding="utf-8")
            )

    def test_markdown_and_html_output_collision_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)
            (source / "index.md").write_text("# Markdown\n", encoding="utf-8")
            (source / "index.html").write_text(
                "<!DOCTYPE html><html><body>HTML</body></html>", encoding="utf-8"
            )

            with self.assertRaisesRegex(builder.ArtifactError, "output collision"):
                builder.build(source, source / "output")

    def test_missing_entrypoint_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)
            (source / "notes.md").write_text("# Notes\n", encoding="utf-8")

            with self.assertRaisesRegex(builder.ArtifactError, "index.html or prototype/index.md"):
                builder.build(source, source / "output")


if __name__ == "__main__":
    unittest.main()
