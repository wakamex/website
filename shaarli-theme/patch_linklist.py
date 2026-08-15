#!/usr/bin/env python3
"""Apply the small Refined markup override to Shaarli's link list."""

import argparse
from pathlib import Path


ORIGINAL = """\
                      {$value.created|format_date}
                      {if="$value.updated_timestamp"}*{/if}
                      &middot;
                    </span>
                  {/if}
                  {$strPermalinkLc}
"""

REFINED = """\
                      {$value.created|format_date}
                      {if="$value.updated_timestamp"}*{/if}
                    </span>
                  {else}
                    {$strPermalinkLc}
                  {/if}
"""


def apply_patch(content: str) -> tuple[str, bool]:
    if REFINED in content:
        return content, False
    if content.count(ORIGINAL) != 1:
        raise ValueError(
            "Shaarli linklist template changed upstream; refusing to apply the "
            "Refined permalink patch"
        )
    return content.replace(ORIGINAL, REFINED), True


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("template", type=Path)
    args = parser.parse_args()

    content = args.template.read_text(encoding="utf-8")
    patched, changed = apply_patch(content)
    if changed:
        args.template.write_text(patched, encoding="utf-8")
        print(f"patched {args.template}")
    else:
        print(f"already patched {args.template}")


if __name__ == "__main__":
    main()
