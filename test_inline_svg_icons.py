import importlib.util
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).parent / "shaarli-theme" / "inline_svg_icons.py"
SPEC = importlib.util.spec_from_file_location("inline_svg_icons", MODULE_PATH)
assert SPEC and SPEC.loader
icons = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(icons)


CSS = (
    '.fa-search:before{content:"\\f002"}'
    '.fa-chevron-up:before{content:"\\f077"}'
    '.fa-chevron-down:before{content:"\\f078"}'
    '.fa-eye:before{content:"\\f06e"}'
    '.fa-eye-slash:before{content:"\\f070"}'
)

FONT = """\
<svg xmlns="http://www.w3.org/2000/svg"><defs>
<font horiz-adv-x="100"><font-face units-per-em="100" ascent="80" />
<glyph unicode="&#xf002;" horiz-adv-x="90" d="M0 0L10 10" />
<glyph unicode="&#xf077;" d="M0 0L20 20" />
<glyph unicode="&#xf078;" d="M0 20L20 0" />
<glyph unicode="&#xf06e;" d="M0 5L20 5" />
<glyph unicode="&#xf070;" d="M0 10L20 10" />
</font></defs></svg>
"""

READ_IT_LATER = """\
function readitlater_get_icon($conf, $isUnread) {
    return '<i class="fa fa-eye' . ($isUnread ? '-slash' : '') . '" aria-hidden="true"></i>';
}
"""


class InlineSvgIconTests(unittest.TestCase):
    def make_root(self, temporary: str) -> Path:
        root = Path(temporary)
        templates = root / "tpl/default"
        fonts = templates / "fonts"
        css = templates / "css"
        plugin = root / "plugins/readitlater"
        fonts.mkdir(parents=True)
        css.mkdir()
        plugin.mkdir(parents=True)
        (css / "shaarli.min.css").write_text(CSS, encoding="utf-8")
        (fonts / "forkawesome-webfont.svg").write_text(FONT, encoding="utf-8")
        (templates / "page.header.html").write_text(
            '<header><i class="fa fa-search" aria-hidden="true"></i></header>',
            encoding="utf-8",
        )
        (templates / "linklist.html").write_text(
            '<button><i class="fa fa-chevron-up" aria-hidden="true"></i></button>',
            encoding="utf-8",
        )
        (templates / "js").mkdir()
        (templates / "js/shaarli.min.js").write_text(
            'classList.toggle("fa-chevron-down")', encoding="utf-8"
        )
        (plugin / "readitlater.php").write_text(READ_IT_LATER, encoding="utf-8")
        return root

    def test_install_replaces_tags_and_embeds_needed_symbols(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_root(temporary)

            replaced, icon_count = icons.install(root)

            header = (root / "tpl/default/page.header.html").read_text()
            linklist = (root / "tpl/default/linklist.html").read_text()
            plugin = (root / "plugins/readitlater/readitlater.php").read_text()
            self.assertEqual(3, replaced)
            self.assertEqual(5, icon_count)
            self.assertNotIn('<i class="fa ', header + linklist + plugin)
            self.assertIn('class="svg-icon fa-search"', header)
            self.assertIn('id="icon-search" viewBox="0 0 90 100"', header)
            self.assertIn('transform="translate(0 80) scale(1 -1)"', header)
            self.assertIn('id="icon-chevron-down"', header)
            self.assertIn('class="svg-icon-chevron-down"', linklist)
            self.assertIn('href="#icon-eye\' . ', plugin)

    def test_install_is_idempotent(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_root(temporary)
            icons.install(root)
            paths = sorted(path for path in root.rglob("*") if path.is_file())
            first = {path: path.read_bytes() for path in paths}

            replaced, icon_count = icons.install(root)

            self.assertEqual(0, replaced)
            self.assertEqual(5, icon_count)
            self.assertEqual(first, {path: path.read_bytes() for path in paths})

    def test_unrecognized_dynamic_font_tag_fails_before_writes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = self.make_root(temporary)
            plugin = root / "plugins/readitlater/readitlater.php"
            plugin.write_text(
                '<i class="fa fa-eye' + "' . $unexpected . '" + '"></i>',
                encoding="utf-8",
            )
            original_header = (root / "tpl/default/page.header.html").read_text()

            with self.assertRaisesRegex(ValueError, "unconverted ForkAwesome"):
                icons.install(root)

            self.assertEqual(
                original_header,
                (root / "tpl/default/page.header.html").read_text(),
            )


if __name__ == "__main__":
    unittest.main()
