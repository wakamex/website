#!/usr/bin/env python3
"""Replace Shaarli's ForkAwesome markup with an inline SVG sprite."""

import argparse
import html
import os
import re
import stat
import tempfile
from pathlib import Path
from xml.etree import ElementTree


SVG_NAMESPACE = "{http://www.w3.org/2000/svg}"
SPRITE_START = "<!-- GENERATED INLINE ICON SPRITE:START -->"
SPRITE_END = "<!-- GENERATED INLINE ICON SPRITE:END -->"
ICON_TAG_RE = re.compile(r"<i\b(?P<attrs>[^>]*)>\s*</i>")
CLASS_RE = re.compile(r'\bclass=(?P<quote>["\'])(?P<value>.*?)(?P=quote)')
ICON_RULE_RE = re.compile(
    r'((?:\.fa-[a-z0-9-]+:before,?)+)\{content:"([^"]+)"\}'
)
READ_IT_LATER_ICON = (
    "return '<i class=\"fa fa-eye' . ($isUnread ? '-slash' : '') . "
    "'\" aria-hidden=\"true\"></i>';"
)
READ_IT_LATER_SVG = (
    "return '<svg class=\"svg-icon fa-eye' . ($isUnread ? '-slash' : '') . "
    "'\" aria-hidden=\"true\"><use href=\"#icon-eye' . "
    "($isUnread ? '-slash' : '') . '\"></use></svg>';"
)
COMMENT_REPLACEMENTS = {
    "Get ForkAwesome icon for the default theme, failback on text.":
        "Get inline SVG icon for the default theme, failback on text.",
    "For the default theme we use a FontAwesome icon which is better than an image":
        "For the default theme we use an inline SVG icon",
}


def icon_codepoints(css: str) -> dict[str, int]:
    icons: dict[str, int] = {}
    for match in ICON_RULE_RE.finditer(css):
        value = match.group(2)
        if value.startswith("\\"):
            codepoint = int(value[1:], 16)
        elif len(value) == 1:
            codepoint = ord(value)
        else:
            raise ValueError(f"unsupported ForkAwesome content value: {value!r}")
        for name in re.findall(r"\.fa-([a-z0-9-]+):before", match.group(1)):
            icons[name] = codepoint
    if not icons:
        raise ValueError("no ForkAwesome icon mappings found in Shaarli CSS")
    return icons


def font_glyphs(font_path: Path) -> tuple[dict[int, tuple[int, str]], int, int]:
    root = ElementTree.parse(font_path).getroot()
    font = next(root.iter(SVG_NAMESPACE + "font"))
    face = next(font.iter(SVG_NAMESPACE + "font-face"))
    default_width = int(font.attrib["horiz-adv-x"])
    units_per_em = int(face.attrib["units-per-em"])
    ascent = int(face.attrib["ascent"])
    glyphs: dict[int, tuple[int, str]] = {}
    for glyph in font.iter(SVG_NAMESPACE + "glyph"):
        character = glyph.attrib.get("unicode", "")
        path = glyph.attrib.get("d")
        if len(character) != 1 or not path:
            continue
        glyphs[ord(character)] = (
            int(glyph.attrib.get("horiz-adv-x", default_width)),
            path,
        )
    if not glyphs:
        raise ValueError("no glyphs found in ForkAwesome SVG font")
    return glyphs, units_per_em, ascent


def icon_name(attrs: str, known_icons: set[str]) -> str | None:
    class_match = CLASS_RE.search(attrs)
    if not class_match:
        return None
    candidates = [
        token[3:]
        for token in class_match.group("value").split()
        if token.startswith("fa-") and token[3:] in known_icons
    ]
    if not candidates:
        return None
    if len(candidates) != 1:
        raise ValueError(f"icon tag contains multiple ForkAwesome glyphs: {attrs}")
    return candidates[0]


def svg_tag(attrs: str, name: str) -> str:
    class_match = CLASS_RE.search(attrs)
    if class_match is None:
        raise ValueError(f"icon tag has no class attribute: {attrs}")
    classes = class_match.group("value").split()
    classes = ["svg-icon", *(token for token in classes if token != "fa")]
    replacement = f'class={class_match.group("quote")}{" ".join(classes)}{class_match.group("quote")}'
    svg_attrs = attrs[: class_match.start()] + replacement + attrs[class_match.end() :]
    if name in {"chevron-up", "chevron-down"}:
        contents = (
            '<use class="svg-icon-chevron-up" href="#icon-chevron-up"></use>'
            '<use class="svg-icon-chevron-down" href="#icon-chevron-down"></use>'
        )
    else:
        contents = f'<use href="#icon-{name}"></use>'
    return f"<svg{svg_attrs}>{contents}</svg>"


def replace_icon_tags(content: str, known_icons: set[str]) -> tuple[str, set[str]]:
    used: set[str] = set()

    def replace(match: re.Match[str]) -> str:
        attrs = match.group("attrs")
        name = icon_name(attrs, known_icons)
        if name is None:
            return match.group(0)
        used.add(name)
        if name in {"chevron-up", "chevron-down"}:
            used.update(("chevron-up", "chevron-down"))
        return svg_tag(attrs, name)

    replaced = ICON_TAG_RE.sub(replace, content)
    return replaced, used


def discover_icon_names(contents: list[str], known_icons: set[str]) -> set[str]:
    names: set[str] = set()
    for content in contents:
        names.update(
            name
            for name in re.findall(r"\bfa-([a-z0-9-]+)", content)
            if name in known_icons
        )
    if "eye" in names:
        names.add("eye-slash")
    if names.intersection({"chevron-up", "chevron-down"}):
        names.update(("chevron-up", "chevron-down"))
    return names


def render_sprite(
    names: set[str],
    codepoints: dict[str, int],
    glyphs: dict[int, tuple[int, str]],
    units_per_em: int,
    ascent: int,
) -> str:
    symbols = []
    for name in sorted(names):
        codepoint = codepoints[name]
        if codepoint not in glyphs:
            raise ValueError(f"ForkAwesome font has no glyph for fa-{name}")
        width, path = glyphs[codepoint]
        symbols.append(
            f'  <symbol id="icon-{name}" viewBox="0 0 {width} {units_per_em}">'
            f'<path transform="translate(0 {ascent}) scale(1 -1)" '
            f'd="{html.escape(path, quote=True)}"></path></symbol>'
        )
    return "\n".join(
        (
            SPRITE_START,
            "<!-- Glyphs extracted from Shaarli's installed ForkAwesome SVG font. -->",
            '<svg class="svg-icon-sprite" aria-hidden="true" '
            'xmlns="http://www.w3.org/2000/svg">',
            *symbols,
            "</svg>",
            SPRITE_END,
        )
    )


def install_sprite(content: str, sprite: str) -> tuple[str, bool]:
    if SPRITE_START in content or SPRITE_END in content:
        pattern = re.compile(
            re.escape(SPRITE_START) + r".*?" + re.escape(SPRITE_END), re.DOTALL
        )
        if len(pattern.findall(content)) != 1:
            raise ValueError("page header has incomplete or duplicate SVG sprites")
        replaced = pattern.sub(sprite, content)
    else:
        replaced = sprite + "\n" + content
    return replaced, replaced != content


def atomic_write(path: Path, content: str) -> None:
    reference = path.stat()
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", text=True
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, stat.S_IMODE(reference.st_mode))
        os.chown(temporary, reference.st_uid, reference.st_gid)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def install(root: Path) -> tuple[int, int]:
    stock_css = (root / "tpl/default/css/shaarli.min.css").read_text(encoding="utf-8")
    codepoints = icon_codepoints(stock_css)
    known_icons = set(codepoints)
    glyphs, units_per_em, ascent = font_glyphs(
        root / "tpl/default/fonts/forkawesome-webfont.svg"
    )

    paths = sorted(
        path
        for directory in (root / "tpl/default", root / "plugins")
        if directory.exists()
        for path in directory.rglob("*")
        if path.suffix in {".html", ".js", ".php"}
    )
    original = {path: path.read_text(encoding="utf-8") for path in paths}
    names = discover_icon_names(list(original.values()), known_icons)
    patched: dict[Path, str] = {}
    replaced_count = 0

    for path, content in original.items():
        updated, used = replace_icon_tags(content, known_icons)
        replaced_count += len(ICON_TAG_RE.findall(content)) - len(ICON_TAG_RE.findall(updated))
        if READ_IT_LATER_ICON in updated:
            updated = updated.replace(READ_IT_LATER_ICON, READ_IT_LATER_SVG)
            replaced_count += 1
            names.update(("eye", "eye-slash"))
        for old, new in COMMENT_REPLACEMENTS.items():
            updated = updated.replace(old, new)
        if updated != content:
            patched[path] = updated

    remaining = [
        str(path.relative_to(root))
        for path, content in {**original, **patched}.items()
        if any(
            (class_match := CLASS_RE.search(match.group("attrs"))) is not None
            and "fa" in class_match.group("value").split()
            for match in ICON_TAG_RE.finditer(content)
        )
    ]
    if remaining:
        raise ValueError("unconverted ForkAwesome tags remain in: " + ", ".join(remaining))

    header_path = root / "tpl/default/page.header.html"
    header = patched.get(header_path, original[header_path])
    sprite = render_sprite(names, codepoints, glyphs, units_per_em, ascent)
    header, _ = install_sprite(header, sprite)
    patched[header_path] = header

    for path, content in patched.items():
        if content != original[path]:
            atomic_write(path, content)
    return replaced_count, len(names)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path, help="Shaarli installation root")
    args = parser.parse_args()

    replaced, icons = install(args.root)
    print(f"installed inline SVG sprite with {icons} icons; replaced {replaced} tags")


if __name__ == "__main__":
    main()
