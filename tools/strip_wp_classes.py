#!/usr/bin/env python3
"""
Strip the WordPress class attributes out of the imported HTML.

Of the 160 class attributes carried over from WordPress, the stylesheet uses
exactly two. The rest — wp-block-paragraph, has-text-color, has-large-font-size
and friends — are inert: they styled nothing here, and they made the content
hard to read and edit. This is a static site now; presentation belongs to the
stylesheet.

    python3 tools/strip_wp_classes.py

Idempotent. `gallery` and `aligncenter` are kept because CSS targets them.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KEEP = {"gallery", "aligncenter"}
# Bookkeeping attributes WordPress emitted for its own editor and lightbox.
DEAD_ATTRS = ("id", "title", "aria-describedby", "data-id", "data-link",
              "data-full-url", "loading", "decoding")


def clean_attrs(tag: str) -> str:
    def class_repl(m):
        kept = [c for c in m.group(1).split() if c in KEEP]
        return f' class="{" ".join(kept)}"' if kept else ""
    tag = re.sub(r'\s*class="([^"]*)"', class_repl, tag)
    for a in DEAD_ATTRS:
        # keep id on anchors that something might link to; drop WordPress's
        if a == "id" and "<a " in tag:
            continue
        tag = re.sub(rf'\s*{a}="[^"]*"', "", tag)
    return tag


def main():
    files = sorted(ROOT.glob("content/pages/*.html")) + sorted(ROOT.glob("content/posts/*.html"))
    before = after = 0
    changed = 0
    for f in files:
        s = original = f.read_text(encoding="utf-8")
        before += len(s)
        s = re.sub(r"<[a-zA-Z][^>]*>", lambda m: clean_attrs(m.group(0)), s)
        s = re.sub(r"[ \t]+>", ">", s)
        s = re.sub(r"\n{3,}", "\n\n", s)
        after += len(s)
        if s != original:
            f.write_text(s, encoding="utf-8")
            changed += 1
    print(f"  {changed} of {len(files)} files rewritten")
    print(f"  {before/1024:.0f} KB -> {after/1024:.0f} KB ({100 - after/before*100:.0f}% smaller)")


if __name__ == "__main__":
    main()
