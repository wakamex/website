import copy
import tempfile
import unittest
from pathlib import Path

import build_autoresearch as builder


def sample_case(number, *, featured_rank=None, links=None):
    case = {
        "case": number,
        "slug": f"{number:02d}-sample",
        "filename": f"{number:02d}-sample.md",
        "title": f"Sample case {number}",
        "started": f"2026-01-{number:02d}",
        "ended": f"2026-01-{number + 1:02d}",
        "summary_markdown": f"Sample **markdown** {number}.",
        "summary_text": f"Sample text {number}.",
        "word_count": 100 + number,
        "token_estimate": {
            "processed_tokens": 100_000_000 + number,
            "effective_tokens": 10_000_000 + number,
            "confidence": "high",
        },
        "featured_rank": featured_rank,
        "report_url": f"https://example.com/reports/{number}",
        "raw_url": f"https://example.com/reports/{number}.txt",
    }
    if links is not None:
        case["links"] = links
    return case


class AutoresearchBuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.feed = {
            "schema_version": 2,
            "title": "Sample collection",
            "description": "Sample collection description.",
            "updated": "2026-01-03",
            "repository_url": "https://example.com/repository",
            "token_estimates": {
                "processed_tokens": 200_000_003,
                "effective_tokens": 20_000_003,
                "method": "Sample audited estimate.",
            },
            "cases": [
                sample_case(
                    1,
                    featured_rank=2,
                    links=[{"text": "Project one", "url": "https://example.com/project"}],
                ),
                sample_case(2, featured_rank=1),
            ],
        }

    def test_shuffled_cases_render_in_case_order(self):
        feed = copy.deepcopy(self.feed)
        feed["cases"].reverse()
        rendered = builder.render_collection(builder.validate_feed(feed))
        positions = [rendered.index(f'id="case-{number}"') for number in (1, 2)]
        self.assertEqual(positions, sorted(positions))

    def test_featured_cases_follow_featured_rank(self):
        rendered = builder.render_featured(builder.validate_feed(copy.deepcopy(self.feed)))
        ranked_cases = sorted(
            (case for case in self.feed["cases"] if case["featured_rank"] is not None),
            key=lambda case: case["featured_rank"],
        )
        positions = [rendered.index(f'CASE {case["case"]}') for case in ranked_cases]
        self.assertEqual(positions, sorted(positions))

    def test_featured_cases_use_compact_source_content(self):
        rendered = builder.render_featured(builder.validate_feed(copy.deepcopy(self.feed)))
        self.assertIn("Featured Autoresearch", rendered)
        for case in self.feed["cases"]:
            if case["featured_rank"] is None:
                continue
            self.assertIn(f'CASE {case["case"]} ({case["started"]})', rendered)
            self.assertIn(case["summary_text"], rendered)
            self.assertNotIn(case["title"], rendered)
        self.assertNotIn('class="research-entry', rendered)

    def test_new_case_and_changed_text_need_no_template_change(self):
        feed = copy.deepcopy(self.feed)
        new_case = copy.deepcopy(feed["cases"][-1])
        new_case.update(
            case=99,
            slug="99-new-case",
            filename="99-new-case.md",
            title="A <new> case",
            summary_text="Exact source text & outcome.",
            featured_rank=None,
            report_url="https://example.com/report",
            raw_url="https://example.com/report.txt",
        )
        feed["cases"].append(new_case)
        rendered = builder.render_collection(builder.validate_feed(feed))
        self.assertIn('id="case-99"', rendered)
        self.assertIn("Exact source text &amp; outcome.", rendered)
        self.assertNotIn("A &lt;new&gt; case", rendered)
        self.assertNotIn(new_case["summary_markdown"], rendered)

    def test_optional_links_may_be_absent(self):
        feed = copy.deepcopy(self.feed)
        feed["cases"][0].pop("links")
        rendered = builder.render_collection(builder.validate_feed(feed))
        first_case = rendered.split('id="case-1"', 1)[1].split("</article>", 1)[0]
        self.assertNotIn("Projects:", first_case)

    def test_collection_case_is_inline_with_summary_and_compact_metadata(self):
        rendered = builder.render_collection(builder.validate_feed(copy.deepcopy(self.feed)))
        case = self.feed["cases"][0]
        self.assertIn(
            f'<p class="research-summary"><a href="{case["report_url"]}">CASE 1</a> '
            f'{case["summary_text"]}</p>',
            rendered,
        )
        self.assertIn("2026-01-01 - 2026-01-02", rendered)
        self.assertIn("10M effective tokens", rendered)
        self.assertNotIn(case["title"], rendered)
        self.assertNotIn("Projects:", rendered)
        self.assertNotIn("Read report", rendered)

    def test_duplicate_case_numbers_fail(self):
        feed = copy.deepcopy(self.feed)
        feed["cases"][1]["case"] = feed["cases"][0]["case"]
        with self.assertRaisesRegex(builder.FeedError, "duplicate case number"):
            builder.validate_feed(feed)

    def test_duplicate_featured_ranks_fail(self):
        feed = copy.deepcopy(self.feed)
        featured = [case for case in feed["cases"] if case["featured_rank"] is not None]
        featured[1]["featured_rank"] = featured[0]["featured_rank"]
        with self.assertRaisesRegex(builder.FeedError, "duplicate featured rank"):
            builder.validate_feed(feed)

    def test_malformed_required_data_fails_clearly(self):
        feed = copy.deepcopy(self.feed)
        feed["cases"][0]["word_count"] = "many"
        with self.assertRaisesRegex(builder.FeedError, r"word_count: expected int, got str"):
            builder.validate_feed(feed)

    def test_invalid_token_estimate_fails_clearly(self):
        feed = copy.deepcopy(self.feed)
        feed["cases"][0]["token_estimate"]["effective_tokens"] = 200_000_000
        with self.assertRaisesRegex(builder.FeedError, "effective tokens exceed processed"):
            builder.validate_feed(feed)

    def test_effective_token_formatting(self):
        self.assertEqual(builder.format_effective_tokens(33_000_000), "33M")
        self.assertEqual(builder.format_effective_tokens(1_320_000_000), "1.32B")

    def test_unsafe_project_url_fails_validation(self):
        feed = copy.deepcopy(self.feed)
        feed["cases"][0]["links"][0]["url"] = "javascript:alert(1)"
        with self.assertRaisesRegex(builder.FeedError, "safe HTTP or HTTPS URL"):
            builder.validate_feed(feed)

    def test_invalid_date_order_fails_validation(self):
        feed = copy.deepcopy(self.feed)
        feed["cases"][0]["started"] = "2026-02-01"
        with self.assertRaisesRegex(builder.FeedError, "started date is after ended date"):
            builder.validate_feed(feed)

    def test_two_builds_are_identical(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            root.joinpath("index.html").write_text(
                f"before\n{builder.START_MARKER}\nold\n{builder.END_MARKER}\nafter\n",
                encoding="utf-8",
            )
            builder.build(copy.deepcopy(self.feed), root)
            first = {
                path.name: path.read_bytes()
                for path in (root / "index.html", root / "autoresearch.html")
            }
            builder.build(copy.deepcopy(self.feed), root)
            second = {
                path.name: path.read_bytes()
                for path in (root / "index.html", root / "autoresearch.html")
            }
            self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
