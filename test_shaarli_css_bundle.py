import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).parent / "shaarli-theme" / "build_css_bundle.py"
SPEC = importlib.util.spec_from_file_location("build_css_bundle", MODULE_PATH)
assert SPEC and SPEC.loader
bundler = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bundler)


PLUGIN_STYLES = """\
{loop="$plugins_includes.css_files"}
  <link type="text/css" rel="stylesheet" href="{$root_path}/{$value}?v={$version_hash}#"/>
{/loop}
"""


def original_includes() -> str:
    return (
        "<title>{$pagetitle}</title>\n"
        + bundler.STOCK_STYLES
        + PLUGIN_STYLES
        + bundler.USER_STYLES
        + '<link rel="search" href="{$base_path}/open-search#" />\n'
    )


class ShaarliCssBundleTests(unittest.TestCase):
    def test_bundle_keeps_source_order_and_relative_urls(self):
        stock = (
            '.thumb{background:url(../img/thumb.png)}\n'
            '/*!\nFork Awesome 1.2.0\n*/.fa-search:before{content:"\\f002"}'
            ':root{--main-color:#000}.page{color:white}'
        )
        markdown = ".markdown{color:gray}"
        refined = "body{background:black}"

        bundle = bundler.build_bundle(stock, markdown, refined)

        self.assertLess(bundle.index(".thumb"), bundle.index(markdown))
        self.assertLess(bundle.index(markdown), bundle.index(refined))
        self.assertNotIn("ForkAwesome", bundle)
        self.assertNotIn("forkawesome-webfont", bundle)
        self.assertIn("url(../img/thumb.png)", bundle)
        self.assertIn(":root{--main-color:#000}", bundle)
        self.assertNotIn("fa-search", bundle)

    def test_template_uses_only_hashed_bundle_and_keeps_plugin_styles(self):
        patched, changed = bundler.patch_includes(original_includes(), "0123456789abcdef")

        self.assertTrue(changed)
        self.assertNotIn("shaarli.min.css", patched)
        self.assertNotIn("markdown.min.css", patched)
        self.assertNotIn("data/user.css", patched)
        self.assertIn(PLUGIN_STYLES, patched)
        self.assertIn("site-refined.css?v=0123456789abcdef", patched)
        self.assertLess(patched.index(PLUGIN_STYLES), patched.index("site-refined.css"))

    def test_template_patch_is_idempotent_and_updates_hash(self):
        first, _ = bundler.patch_includes(original_includes(), "0123456789abcdef")
        same, changed = bundler.patch_includes(first, "0123456789abcdef")
        updated, updated_changed = bundler.patch_includes(first, "fedcba9876543210")

        self.assertFalse(changed)
        self.assertEqual(first, same)
        self.assertTrue(updated_changed)
        self.assertIn("site-refined.css?v=fedcba9876543210", updated)

    def test_unknown_upstream_template_fails_without_partial_patch(self):
        changed = original_includes().replace("shaarli.min.css", "new-name.css")

        with self.assertRaisesRegex(ValueError, "changed upstream"):
            bundler.patch_includes(changed, "0123456789abcdef")

    def test_install_writes_bundle_and_patches_template(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            css_dir = root / "tpl/default/css"
            css_dir.mkdir(parents=True)
            (css_dir / "shaarli.min.css").write_text(
                '/*!\nFork Awesome 1.2.0\n*/.fa-search:before{content:"\\f002"}'
                ':root{--main-color:#000}',
                encoding="utf-8",
            )
            (css_dir / "markdown.min.css").write_text(
                ".markdown{color:gray}", encoding="utf-8"
            )
            includes = root / "tpl/default/includes.html"
            includes.write_text(original_includes(), encoding="utf-8")
            refined = root / "refined.css"
            refined.write_text("body{background:black}", encoding="utf-8")

            bundle_path, digest, changed = bundler.install(root, refined)

            bundle = bundle_path.read_text(encoding="utf-8")
            self.assertTrue(changed)
            self.assertEqual(hashlib.sha256(bundle.encode()).hexdigest()[:16], digest)
            self.assertIn("site-refined.css?v=" + digest, includes.read_text())


if __name__ == "__main__":
    unittest.main()
