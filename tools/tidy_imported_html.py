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
HEADING_MAPS = {
    # the five services are siblings; WordPress had three of them as h5
    "professional-services":               {5: 3},
    # "Relevant certifications" sat at h3 above the h2s that followed it
    "penetration-testing-services":        {3: 2, 4: 3},
    "web-application-penetration-testing": {3: 2, 4: 3},
    # "Industry Standards" and "GlobeTech CUSTOMIZATION" were h6
    "wifi-testing-services":               {6: 3},
}

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


def remap_headings(body: str, mapping: dict[int, int]) -> str:
    def repl(m):
        old = int(m.group(2))
        new = mapping.get(old, old)
        return f"<{m.group(1)}h{new}{m.group(3)}"
    return re.sub(r"<(/?)h([1-6])([^>]*>)",
                  lambda m: repl(m) if m.group(2).isdigit() else m.group(0), body)


def strip_pinned_sizes(body: str) -> str:
    """Remove inline width/height so the stylesheet controls image sizing.

    These produced images at 320, 415, 480, 640, 752 and 765 pixels down the
    same column. The width/height *attributes* are kept — they give the browser
    the aspect ratio and prevent layout shift."""
    def repl(m):
        style = m.group(1)
        style = re.sub(r"\s*(?:width|height)\s*:\s*[^;]+;?", "", style)
        return f' style="{style.strip()}"' if style.strip() else ""
    return re.sub(r'\s*style="([^"]*)"', repl, body)


def group_figure_runs(body: str) -> str:
    """Two or more consecutive figures become a row instead of a tall stack."""
    def repl(m):
        block = m.group(0)
        if 'class="figure-row"' in block:
            return block
        n = block.count("<figure")
        return f'<div class="figure-row figure-row-{min(n, 3)}">\n{block.strip()}\n</div>'
    return re.sub(r'(?:<figure[^>]*>.*?</figure>\s*){2,}', repl, body, flags=re.S)


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

        if slug in HEADING_MAPS:
            body = remap_headings(body, HEADING_MAPS[slug])
            notes.append("headings")
        if 'style="' in body:
            body = strip_pinned_sizes(body)
            notes.append("pinned sizes")
        if slug in DROP_TRAILING_CONTACT and re.search(r'<h2[^>]*>\s*Contact\s*</h2>', body, re.I):
            body = drop_trailing_contact(body)
            notes.append("trailing CTA")
        grouped = group_figure_runs(body)
        if grouped != body:
            body = grouped
            notes.append("figure rows")

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
            body = strip_pinned_sizes(body)
            notes.append("pinned sizes")
        grouped = group_figure_runs(body)
        if grouped != body:
            body = grouped
            notes.append("figure rows")
        if body != original:
            f.write_text(body, encoding="utf-8")
            print(f"  {p['slug'][:44]:<46} {', '.join(notes)}")
        else:
            print(f"  {p['slug'][:44]:<46} (unchanged)")


if __name__ == "__main__":
    main()
    tidy_posts()
