import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import publish_usage


class PublicDocumentTests(unittest.TestCase):
    def test_agy_publishes_only_quota_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            caches = {key: root / f"{key}.json" for key in ("claude", "codex", "agy")}
            caches["claude"].write_text(json.dumps({"plan": "max", "7d": {"pct": 37}}))
            caches["agy"].write_text(json.dumps({
                "plan": "Google AI Pro",
                "updated_at": "2026-10-03T00:00:00+00:00",
                "history": {"top_commands": {"private prompt": 1}},
                "project_root": "/home/someone",
                "model": "Gemini",
                "quota_summary": {"plan": "Pro", "groups": [], "project_id": "secret-project"},
            }))
            with mock.patch.object(publish_usage, "CACHES", caches):
                document = publish_usage.public_document()

        self.assertEqual({"claude", "agy"}, set(document))
        self.assertEqual({"plan", "updated_at", "quota_summary"}, set(document["agy"]))
        self.assertEqual({"plan": "Pro", "groups": []}, document["agy"]["quota_summary"])
        self.assertNotIn("private prompt", publish_usage.render(document))

    def test_unreadable_cache_is_skipped(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            caches = {"claude": root / "claude.json", "codex": root / "codex.json"}
            caches["claude"].write_text("{truncated")
            caches["codex"].write_text(json.dumps({"plan": "pro"}))
            with mock.patch.object(publish_usage, "CACHES", caches), mock.patch.object(publish_usage, "log"):
                document = publish_usage.public_document()

        self.assertEqual({"codex": {"plan": "pro"}}, document)


if __name__ == "__main__":
    unittest.main()
