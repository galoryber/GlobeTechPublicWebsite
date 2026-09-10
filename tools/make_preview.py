#!/usr/bin/env python3
"""
Bundle dist/index.html into one self-contained HTML file.

Inlines the stylesheet, the font, and every image as data URIs so the page
renders with no network access at all — useful for previewing the site from a
terminal-only session, or emailing it to a bandmate.

    python3 tools/make_preview.py [output.html]

Third-party embeds (Spotify, YouTube) can't load in a sandboxed preview, so
they're swapped for labelled placeholders rather than left as dead frames.
"""

import base64
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "preview.html"

MIME = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
        ".svg": "image/svg+xml", ".woff2": "font/woff2"}


def data_uri(rel_path: str) -> str | None:
    path = DIST / rel_path.lstrip("/")
    if not path.is_file():
        print(f"  !! missing asset {rel_path}")
        return None
    mime = MIME.get(path.suffix.lower(), "application/octet-stream")
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"


PLACEHOLDER = """<div style="position:absolute;inset:0;display:grid;place-items:center;
     text-align:center;padding:24px;background:var(--surface-2);color:var(--text-muted)">
  <div>
    <div style="font-family:var(--mono);letter-spacing:.14em;text-transform:uppercase;
                font-size:.8rem;color:var(--signal);margin-bottom:8px">{label}</div>
    <div style="font-size:.92rem">Loads on the live site — third-party embeds are<br>blocked in this offline preview.</div>
  </div>
</div>"""


def main():
    html = (DIST / "index.html").read_text(encoding="utf-8")

    # Stylesheet -> inline <style>, with the font swapped to a data URI.
    css = (DIST / "css" / "site.css").read_text(encoding="utf-8")
    for face in ("plex-sans.woff2", "plex-mono.woff2"):
        font = data_uri(f"/fonts/{face}")
        if font:
            css = css.replace(f'url("/fonts/{face}")', f'url("{font}")')
    html = re.sub(r'\s*<link rel="stylesheet" href="/css/site\.css">',
                  f"\n  <style>\n{css}\n  </style>", html)

    # Drop links that can't resolve offline.
    html = re.sub(r'\s*<link rel="preload"[^>]*>', "", html)
    html = re.sub(r'\s*<link rel="icon"[^>]*>', "", html)
    html = re.sub(r'\s*<script src="[^"]*"[^>]*></script>', "", html)

    # Images -> data URIs.
    inlined = 0
    def sub_img(match):
        nonlocal inlined
        uri = data_uri(match.group(1))
        if not uri:
            return match.group(0)
        inlined += 1
        return f'src="{uri}"'
    html = re.sub(r'src="(/img/[^"]+)"', sub_img, html)

    # Iframes -> labelled placeholders.
    def sub_iframe(match):
        tag = match.group(0)
        label = "Spotify playlist" if "spotify" in tag else "YouTube video"
        return PLACEHOLDER.format(label=label)
    html = re.sub(r"<iframe.*?</iframe>", sub_iframe, html, flags=re.S)

    # The Spotify block sizes itself from the iframe; give it a height.
    html = html.replace('<div class="spotify-embed">',
                        '<div class="spotify-embed" style="position:relative;height:220px">')

    # Only the home page is bundled, so point in-site links at nothing rather
    # than letting them lead to a dead end.
    html = re.sub(r'href="/(about|services|pricing|contact|blog)/"', 'href="#" data-inert', html)
    html = re.sub(r"<title>.*?</title>", "<title>GlobeTech Rebuild</title>",
                  html, count=1, flags=re.S)

    banner = """<div style="background:#f2f1ed;border-bottom:1px solid #e3e0da;color:#626c78;
     font:600 13px/1.5 ui-sans-serif,system-ui,sans-serif;padding:11px 20px;text-align:center">
  Offline preview of the <strong style="color:#131820">home page</strong>.
  Navigation and embeds are inactive here — everything works on the live site.
</div>"""
    html = html.replace("<body>", f"<body>\n{banner}", 1)

    OUT.write_text(html, encoding="utf-8")
    size_mb = OUT.stat().st_size / 1_048_576
    print(f"Preview -> {OUT}  ({size_mb:.2f} MB, {inlined} images inlined)")


if __name__ == "__main__":
    main()
