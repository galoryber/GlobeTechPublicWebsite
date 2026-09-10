#!/usr/bin/env python3
"""
One-shot tidy of the HTML imported from WordPress.

WordPress pages were authored by picking headings for their visual size rather
than their meaning, and by pinning image dimensions inline. That produced
heading sequences that skip levels (h2 -> h6 on one page) and a column of
images at six different widths. Neither is fixable from CSS.

    python3 tools/tidy_imported_html.py

Rewrites content/pages/*.html in place. Safe to re-run: every change is
idempotent.
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGES = ROOT / "content" / "pages"

# Heading levels are remapped per page rather than by a generic rule, because
# the correct level depends on what the heading means. The page title is an h1
# in the template, so body headings start at h2.
# Trailing "Contact" sections repeat a call to action the layout already
# renders as a band at the foot of every page.
DROP_TRAILING_CONTACT = {
    "professional-services", "penetration-testing-services",
    "web-application-penetration-testing", "wifi-testing-services",
    "external-vulnerability-scanning", "internal-vulnerability-scanning",
}


def normalise_outline(body: str) -> str:
    """Rewrite heading levels into a valid outline starting at h2.

    Blog posts were the worst of it: one starts at h4 and uses nothing else,
    another runs h2 -> h6, a third opens at h5. Hand-mapping eleven posts would
    be guesswork, so relative nesting is inferred from the original levels and
    re-emitted contiguously. The page/post title is the h1, so bodies start at
    h2 and never skip.
    """
    stack: list[tuple[int, int]] = []          # (original level, emitted level)

    def repl(m):
        nonlocal stack
        closing, level, rest = m.group(1), int(m.group(2)), m.group(3)
        if closing:
            return m.group(0)                   # patched below, in pairs
        while stack and stack[-1][0] >= level:
            stack.pop()
        emitted = min(stack[-1][1] + 1, 6) if stack else 2
        stack.append((level, emitted))
        return f"<h{emitted}{rest}"

    # rewrite openers, remembering what each became, then match the closers
    emitted_levels: list[int] = []

    def repl_open(m):
        out = repl(m)
        emitted_levels.append(int(out[2]))
        return out

    body = re.sub(r"<(/?)h([1-6])([^>]*>)",
                  lambda m: repl_open(m) if not m.group(1) else m.group(0), body)

    it = iter(emitted_levels)
    return re.sub(r"</h[1-6]>", lambda m: f"</h{next(it)}>", body)


def strip_inline_styles(body: str) -> str:
    """Remove inline style attributes from imported markup.

    WordPress carried both pinned pixel sizes (images at 320, 415, 480, 640, 752
    and 765 px down one column) and hard-coded heading colours — magenta
    #d709a4, green #2ff425, orange #ff8606 and others that fight the palette
    entirely. The stylesheet owns presentation now.

    width/height *attributes* are deliberately kept: they give the browser the
    aspect ratio and prevent layout shift.
    """
    return re.sub(r'\s*style="[^"]*"', "", body)


def drop_empty_divs(body: str) -> str:
    """Remove structureless leftovers from stripped WordPress column blocks."""
    body = re.sub(r'<div[^>]*aria-hidden="true"[^>]*>\s*</div>', "", body)
    for _ in range(4):                                   # unwrap nested shells
        body = re.sub(r'<div>\s*(<div>[\s\S]*?</div>)\s*</div>', r"\1", body)
    body = re.sub(r'<div>\s*</div>', "", body)
    return body


def mark_galleries(body: str) -> str:
    """Tag WordPress galleries so CSS can lay them out as a row.

    A gallery is a <figure> whose direct children are <figure> elements. An
    earlier version of this tool tried to *rewrite* runs of figures into a grid
    div and got it badly wrong — the regex ran past the closing tag and
    swallowed headings and paragraphs into the wrapper, wrecking two pages.
    Adding a class and letting CSS do the layout touches nothing else.
    """
    out = []
    depth = 0
    open_positions: list[int] = []
    tokens = re.split(r'(<figure[^>]*>|</figure>)', body)
    # Walk the tokens tracking figure depth; an opening tag at depth 0 whose
    # matching region contains further <figure> opens is a gallery wrapper.
    idx = 0
    while idx < len(tokens):
        tok = tokens[idx]
        if tok.startswith("<figure"):
            if depth == 0:
                # look ahead for a nested figure before this one closes
                d, j, nested = 1, idx + 1, False
                while j < len(tokens) and d > 0:
                    if tokens[j].startswith("<figure"):
                        d += 1; nested = True
                    elif tokens[j].startswith("</figure"):
                        d -= 1
                    j += 1
                if nested and "gallery" not in tok:
                    tok = tok.replace("<figure", '<figure class="gallery"', 1)
            depth += 1
        elif tok.startswith("</figure"):
            depth -= 1
        out.append(tok)
        idx += 1
    return "".join(out)


def drop_trailing_contact(body: str) -> str:
    m = None
    for m in re.finditer(r'<h2[^>]*>\s*Contact\s*</h2>', body, re.I):
        pass
    return body[:m.start()].rstrip() if m else body


def main():
    print("Pages:")
    slugs = [p["slug"] for p in json.loads((ROOT / "content" / "pages.json").read_text())]
    for slug in slugs:
        f = PAGES / f"{slug}.html"
        body = original = f.read_text(encoding="utf-8")
        notes = []

        fixed = normalise_outline(body)
        if fixed != body:
            body = fixed
            notes.append("outline")
        if 'style="' in body:
            body = strip_inline_styles(body)
            notes.append("inline styles")
        cleaned = drop_empty_divs(body)
        if cleaned != body:
            body = cleaned
            notes.append("empty divs")
        if slug in DROP_TRAILING_CONTACT and re.search(r'<h2[^>]*>\s*Contact\s*</h2>', body, re.I):
            body = drop_trailing_contact(body)
            notes.append("trailing CTA")
        marked = mark_galleries(body)
        if marked != body:
            body = marked
            notes.append("galleries")

        if body != original:
            f.write_text(body, encoding="utf-8")
            print(f"  {slug:<40} {', '.join(notes)}")
        else:
            print(f"  {slug:<40} (unchanged)")


def tidy_posts():
    posts_dir = ROOT / "content" / "posts"
    print("\nPosts:")
    for p in json.loads((ROOT / "content" / "posts.json").read_text()):
        f = posts_dir / f'{p["slug"]}.html'
        body = original = f.read_text(encoding="utf-8")
        notes = []
        fixed = normalise_outline(body)
        if fixed != body:
            body = fixed
            notes.append("outline")
        if 'style="' in body:
            body = strip_inline_styles(body)
            notes.append("inline styles")
        cleaned = drop_empty_divs(body)
        if cleaned != body:
            body = cleaned
            notes.append("empty divs")
        marked = mark_galleries(body)
        if marked != body:
            body = marked
            notes.append("galleries")
        if body != original:
            f.write_text(body, encoding="utf-8")
            print(f"  {p['slug'][:44]:<46} {', '.join(notes)}")
        else:
            print(f"  {p['slug'][:44]:<46} (unchanged)")


if __name__ == "__main__":
    main()
    tidy_posts()
