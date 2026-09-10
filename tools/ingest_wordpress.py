#!/usr/bin/env python3
"""
One-shot importer: pull posts, pages and images out of the old WordPress site.

Run once during the migration. Kept in the repo so the import is reproducible
and so it is obvious where the content came from.

    python3 tools/ingest_wordpress.py

Writes:
    content/posts.json        post metadata, newest first
    content/posts/SLUG.html   post body, images rewritten to local paths
    content/pages/SLUG.html   page body, same treatment
    static/img/posts/...      every referenced image, downloaded

Images in the old post HTML point at two hosts. 23 of them point at
http://3.134.223.139, a server that no longer exists — but the files were
carried over to the current host, so those URLs are repaired on the way in.
"""

import html as htmllib
import json
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API = "https://globetech.biz/wp-json/wp/v2"
LIVE_HOST = "https://globetech.biz"
DEAD_HOST = "http://3.134.223.139"

POSTS_DIR = ROOT / "content" / "posts"
PAGES_DIR = ROOT / "content" / "pages"
IMG_DIR = ROOT / "static" / "img" / "posts"


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "globetech-migration/1.0"})
    with urllib.request.urlopen(req, timeout=45) as r:
        return r.read()


def api(path: str):
    return json.loads(fetch(f"{API}/{path}").decode("utf-8"))


def local_name(url: str) -> str:
    """A flat, safe filename for a wp-content upload URL."""
    tail = url.split("/wp-content/uploads/", 1)[-1]
    name = re.sub(r"[^A-Za-z0-9._-]", "-", tail)
    return re.sub(r"-+", "-", name).strip("-")


ASSET_RE = re.compile(
    r'https?://(?:globetech\.biz|3\.134\.223\.139)/wp-content/uploads/[^\s"\'<>()\\]+'
)
MEDIA_SUFFIXES = {".webm", ".mp4", ".m4v", ".ogv", ".mp3", ".wav",
                  ".pdf", ".zip", ".pptx", ".ppt", ".docx", ".xlsx", ".7z", ".tar", ".gz"}


def rewrite_assets(body: str, seen: dict) -> str:
    """Localise every upload URL, whatever attribute or inline style it sits in.

    The old HTML references uploads from <img src>, <a href> (lightbox links to
    the full-size file), <video src>, srcset lists, and at least one inline
    background-image. Matching URLs directly rather than tags catches all of
    them, including any shape not seen yet.
    """
    def repl(match):
        url = htmllib.unescape(match.group(0))
        # The dead host's files still exist on the live host under the same path.
        fixed = url.replace(DEAD_HOST, LIVE_HOST)
        name = local_name(fixed)
        suffix = Path(name).suffix.lower()
        subdir, prefix = ("media", "/media") if suffix in MEDIA_SUFFIXES else ("posts", "/img/posts")
        target = (ROOT / "static" / subdir / name) if subdir == "media" else (IMG_DIR / name)
        if name not in seen:
            target.parent.mkdir(parents=True, exist_ok=True)
            try:
                target.write_bytes(fetch(fixed))
                seen[name] = fixed
                size = target.stat().st_size
                print(f"    + {name} ({size // 1024} KB)")
            except Exception as exc:
                print(f"    !! {fixed} -> {exc}")
                return match.group(0)
        return f"{prefix}/{name}"

    return ASSET_RE.sub(repl, body)


def clean(body: str) -> str:
    """Strip WordPress scaffolding that means nothing outside WordPress."""
    body = re.sub(r"<!--\s*/?wp:.*?-->", "", body)                 # block comments
    body = re.sub(r'\s*class="wp-block-[^"]*"', "", body)
    body = re.sub(r'\s*(?:id|class)="(?:attachment_|wp-image-)[^"]*"', "", body)
    # srcset/sizes reference every thumbnail size WordPress generated — 190 extra
    # files for 98 real images. The src attribute alone is the size the post
    # actually displays, so drop the variant lists.
    body = re.sub(r'\s*(?:srcset|sizes)="[^"]*"', "", body)
    # Gallery/lightbox bookkeeping attributes, some pointing at attachment pages
    # on a server that no longer exists.
    body = re.sub(r'\s*data-(?:id|link|full-url|lightbox-\w+)="[^"]*"', "", body)
    body = re.sub(r'\s*(?:loading|decoding)="[^"]*"', "", body)
    # WordPress injects a hidden oEmbed iframe for internal links. It points at
    # a /embed/ endpoint that will not exist after the migration.
    body = re.sub(r'<iframe[^>]*wp-embedded-content.*?</iframe>', "", body, flags=re.S)
    body = re.sub(r'<blockquote[^>]*wp-embedded-content.*?</blockquote>', "", body, flags=re.S)
    body = re.sub(r"\n{3,}", "\n\n", body)
    return body.strip()


def main():
    for d in (POSTS_DIR, PAGES_DIR, IMG_DIR):
        d.mkdir(parents=True, exist_ok=True)
    seen: dict[str, str] = {}

    print("Posts:")
    posts = api("posts?per_page=100&_fields=id,slug,title,content,excerpt,date,modified")
    meta = []
    for p in posts:
        slug = p["slug"]
        print(f"  {p['date'][:10]}  {slug}")
        body = rewrite_assets(clean(p["content"]["rendered"]), seen)
        (POSTS_DIR / f"{slug}.html").write_text(body, encoding="utf-8")
        excerpt = re.sub(r"<[^>]+>", " ", p["excerpt"]["rendered"])
        excerpt = htmllib.unescape(" ".join(excerpt.split())).replace(" [&hellip;]", "").strip()
        meta.append({
            "slug": slug,
            "title": htmllib.unescape(re.sub(r"<[^>]+>", "", p["title"]["rendered"])),
            "date": p["date"][:10],
            "excerpt": excerpt[:280],
            # the URL WordPress served, so the build can leave a stub behind
            "legacy_path": "/index.php/" + p["date"][:10].replace("-", "/") + f"/{slug}/",
        })
    meta.sort(key=lambda m: m["date"], reverse=True)
    (ROOT / "content" / "posts.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

    print("\nPages:")
    pages = api("pages?per_page=50&_fields=id,slug,title,content,date,link")
    pmeta = []
    for p in pages:
        slug = p["slug"]
        title = htmllib.unescape(re.sub(r"<[^>]+>", "", p["title"]["rendered"])).strip()
        print(f"  {slug or '(no slug)':<40} {title[:40]}")
        body = rewrite_assets(clean(p["content"]["rendered"]), seen)
        (PAGES_DIR / f"{slug}.html").write_text(body, encoding="utf-8")
        pmeta.append({"slug": slug, "title": title, "legacy_path": "/index.php/" + slug + "/"})
    (ROOT / "content" / "pages.json").write_text(json.dumps(pmeta, indent=2) + "\n", encoding="utf-8")

    print(f"\n{len(posts)} posts, {len(pages)} pages, {len(seen)} images downloaded")


if __name__ == "__main__":
    main()
