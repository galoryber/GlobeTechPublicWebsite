#!/usr/bin/env python3
"""
GlobeTech LLC static site builder.

Reads JSON + HTML fragments from content/, copies static/, writes dist/.
Pure standard library — no pip install, no node_modules, nothing to rot.

    python3 build.py

Page and post bodies are HTML imported from the old WordPress site by
tools/ingest_wordpress.py. This wraps them in the layout; it does not rewrite
them. Editing a page means editing content/pages/SLUG.html.
"""

from __future__ import annotations

import datetime as dt
import html
import json
import re
import shutil
from email.utils import format_datetime
from pathlib import Path

ROOT = Path(__file__).parent
CONTENT = ROOT / "content"
STATIC = ROOT / "static"
DIST = ROOT / "dist"

SITE = json.loads((CONTENT / "site.json").read_text(encoding="utf-8"))
BASE = SITE["url"].rstrip("/")


def e(text) -> str:
    return html.escape(str(text if text is not None else ""), quote=True)


def write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def strip_tags(s: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", s)).split())


def first_paragraph(body: str, limit: int = 180) -> str:
    m = re.search(r"<p[^>]*>(.*?)</p>", body, re.S)
    text = strip_tags(m.group(1)) if m else strip_tags(body)
    return (text[:limit].rsplit(" ", 1)[0] + "…") if len(text) > limit else text


def nav_html(current: str) -> str:
    items = [(p["route"], p["nav_label"]) for p in PAGES if p["in_nav"]]
    items.insert(2, ("/blog/", "Blog"))
    return "\n".join(
        f'          <a href="{r}"{" aria-current=\"page\"" if r == current else ""}>{e(l)}</a>'
        for r, l in items
    )


def layout(*, title, description, path, body, extra_head="", body_end=""):
    canonical = BASE + path
    year = dt.date.today().year
    jsonld = {
        "@context": "https://schema.org", "@type": "ProfessionalService",
        "name": SITE["name"], "url": SITE["url"], "description": SITE["description"],
        "address": {"@type": "PostalAddress", "addressRegion": "WI", "addressCountry": "US"},
        "areaServed": "US",
        "serviceType": ["Penetration Testing", "Vulnerability Assessment",
                        "Web Application Security Testing", "Wireless Security Auditing"],
    }
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{e(title)}</title>
  <meta name="description" content="{e(description)}">
  <link rel="canonical" href="{e(canonical)}">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="{e(SITE["name"])}">
  <meta property="og:title" content="{e(title)}">
  <meta property="og:description" content="{e(description)}">
  <meta property="og:url" content="{e(canonical)}">
  <meta name="twitter:card" content="summary">
  <meta name="theme-color" content="#0f1b2d">
  <link rel="icon" href="/img/favicon.svg" type="image/svg+xml">
  <link rel="alternate" type="application/rss+xml" title="{e(SITE["name"])} — Blog" href="/feed.xml">
  <link rel="preload" href="/fonts/plex-sans.woff2" as="font" type="font/woff2" crossorigin>
  <link rel="stylesheet" href="/css/site.css">
  <script type="application/ld+json">
{json.dumps(jsonld, indent=2)}
  </script>
{extra_head}</head>
<body>
  <a class="skip-link" href="#main">Skip to content</a>
  <header class="site-header">
    <div class="wrap">
      <a class="brand" href="/">
        <span class="brand-name">GlobeTech<span>.</span></span>
        <span class="brand-tag">Security Assessments</span>
      </a>
      <nav class="nav" aria-label="Main">
{nav_html(path)}
      </nav>
    </div>
  </header>
  <main id="main">
{body}
  </main>
  <footer class="site-footer">
    <div class="wrap">
      <div class="footer-grid">
        <div>
          <p style="margin:0 0 6px"><strong>{e(SITE["name"])}</strong> — {e(SITE["hometown"])}</p>
          <p style="margin:0">Contact via the chat button, bottom right.</p>
        </div>
        <nav class="nav" aria-label="Footer">
{nav_html("")}
        </nav>
      </div>
      <p class="footer-legal">© {year} {e(SITE["name"])}. All rights reserved.</p>
    </div>
  </footer>
  <call-us-selector phonesystem-url="{e(SITE["chat"]["phonesystem_url"])}"
                    party="{e(SITE["chat"]["party"])}" enable-poweredby="false"></call-us-selector>
  <script defer src="/js/callus.js"></script>
{body_end}</body>
</html>
"""


CTA = """    <section class="cta">
      <div class="wrap">
        <h2>Ready to find out where you stand?</h2>
        <p>Tell us about your environment and what you need to demonstrate. We will
           tell you which assessment actually answers that question.</p>
        <a class="btn btn-primary" href="/contact/">Get in touch</a>
      </div>
    </section>"""


def page_body(slug: str) -> str:
    return (CONTENT / "pages" / f"{slug}.html").read_text(encoding="utf-8")


def post_row(p, level: int = 3) -> str:
    """One entry in a post list. `level` is the heading level for the title —
    the blog index puts these under the page h1, the home page under an h2."""
    nice = dt.date.fromisoformat(p["date"]).strftime("%b %-d, %Y")
    return f"""          <li><a class="post-link" href="/blog/{e(p["slug"])}/">
            <time datetime="{e(p["date"])}">{nice}</time>
            <span><h{level}>{e(p["title"])}</h{level}><p>{e(p["excerpt"][:190])}</p></span>
          </a></li>"""


def render_home() -> str:
    """The home page is composed, not imported.

    WordPress emitted this page as a single body with the heading levels out of
    order (h3, then h1, then h4), a stock banner, an unreadable 108px-tall
    screenshot, a duplicate blog list, and six 400px certification badges
    stacked down a text column. Rebuilding it from structured content in
    home.json is what makes the layout controllable.
    """
    services = [p for p in PAGES if p["is_service"]]
    cards = "\n".join(f"""          <a class="card" href="{s_["route"]}">
            <h3>{e(s_["nav_label"])}</h3>
            <p>{e(first_paragraph(page_body(s_["slug"]), 110))}</p>
            <span class="more">Read more &rarr;</span>
          </a>""" for s_ in services)

    recent = "\n".join(post_row(p, 3) for p in POSTS[:4])

    intro = "\n".join(f"          <p>{e(t)}</p>" for t in HOME["intro"])

    caps = "\n".join(f'            <li>{e(c)}</li>' for c in HOME["capabilities"])

    badges = "\n".join(f"""            <li class="badge">
              <img src="/img/badges/{e(c["badge"])}" alt="{e(c["full"])}" width="150" height="150" loading="lazy">
              <span class="badge-name">{e(c["name"])}</span>
            </li>""" for c in HOME["credentials"])

    training = "\n".join(f'            <li>{e(t)}</li>' for t in HOME["training"])

    return layout(
        title=f'{SITE["name"]} | {SITE["tagline"]}',
        description=SITE["description"],
        path="/",
        body=f"""    <section class="hero">
      <div class="wrap">
        <p class="eyebrow">{e(HOME["hero_eyebrow"])}</p>
        <h1>{e(HOME["hero_heading"])}</h1>
        <p class="lede">{e(SITE["description"])}</p>
        <div class="hero-actions">
          <a class="btn btn-primary" href="/contact/">Start a conversation</a>
          <a class="btn btn-ghost" href="/services/">See the services</a>
        </div>
      </div>
    </section>

    <section class="section">
      <div class="wrap">
        <div class="intro-split">
          <div class="prose">
            <h2>{e(HOME["intro_heading"])}</h2>
{intro}
          </div>
          <div class="capabilities">
            <p class="eyebrow">{e(HOME["capabilities_heading"])}</p>
            <ul>
{caps}
            </ul>
          </div>
        </div>
      </div>
    </section>

    <section class="section section-alt">
      <div class="wrap">
        <p class="eyebrow">Services</p>
        <h2>What we assess</h2>
        <div class="grid grid-3" style="margin-top:26px">
{cards}
        </div>
      </div>
    </section>

    <section class="section credentials-band">
      <div class="wrap">
        <p class="eyebrow">{e(HOME["credentials_heading"])}</p>
        <h2>Held, current, and verifiable</h2>
        <p class="standfirst" style="margin-bottom:34px">{e(HOME["credentials_note"])}</p>
        <ul class="badges">
{badges}
        </ul>
        <ul class="training">
{training}
        </ul>
        <p style="margin-top:26px">
          <a class="btn btn-ghost" href="{e(HOME["credly_url"])}">Verify on Credly</a>
        </p>
      </div>
    </section>

    <section class="section">
      <div class="wrap">
        <p class="eyebrow">Writing</p>
        <h2>From the blog</h2>
        <ul class="posts" style="margin-top:24px">
{recent}
        </ul>
        <p style="margin-top:26px"><a class="btn btn-ghost" href="/blog/">All posts</a></p>
      </div>
    </section>

{CTA}""")


def render_page(pg) -> str:
    body_html = page_body(pg["slug"])
    desc = first_paragraph(body_html)

    extra_head = body_end = ""
    widget = ""

    body = f"""    <div class="page-head">
      <div class="wrap">
        <h1>{e(pg["title"])}</h1>
      </div>
    </div>

    <section class="section">
      <div class="wrap">
        <div class="prose">
{body_html}
        </div>{widget}
      </div>
    </section>

{CTA}"""
    return layout(title=f'{pg["title"]} — {SITE["name"]}', description=desc,
                  path=pg["route"], body=body, extra_head=extra_head, body_end=body_end)


def render_post(p) -> str:
    body_html = (CONTENT / "posts" / f'{p["slug"]}.html').read_text(encoding="utf-8")
    nice = dt.date.fromisoformat(p["date"]).strftime("%B %-d, %Y")
    body = f"""    <div class="page-head">
      <div class="wrap narrow">
        <p class="post-meta"><a href="/blog/">Blog</a> · <time datetime="{e(p["date"])}">{nice}</time></p>
        <h1>{e(p["title"])}</h1>
      </div>
    </div>

    <section class="section">
      <div class="wrap narrow">
        <article class="prose">
{body_html}
        </article>
        <p style="margin-top:44px"><a class="btn btn-ghost" href="/blog/">← All posts</a></p>
      </div>
    </section>

{CTA}"""
    return layout(title=f'{p["title"]} — {SITE["name"]}',
                  description=p["excerpt"] or first_paragraph(body_html),
                  path=f'/blog/{p["slug"]}/', body=body)


def render_blog_index() -> str:
    items = "\n".join(post_row(p, 2) for p in POSTS)
    body = f"""    <div class="page-head">
      <div class="wrap">
        <h1>Blog</h1>
        <p class="standfirst">Notes on offensive security — technique write-ups,
           certification reviews, and the occasional opinion.
           <a href="/feed.xml">RSS</a>.</p>
      </div>
    </div>

    <section class="section">
      <div class="wrap">
        <ul class="posts">
{items}
        </ul>
      </div>
    </section>
"""
    return layout(title=f'Blog — {SITE["name"]}',
                  description="Offensive security write-ups, technique notes and certification reviews from GlobeTech LLC.",
                  path="/blog/", body=body)


def render_404() -> str:
    body = """    <section class="section" style="padding:110px 0">
      <div class="wrap narrow">
        <p class="eyebrow">404</p>
        <h1 style="font-size:clamp(1.8rem,4vw,2.6rem);letter-spacing:-.02em;margin:0 0 14px">
          That page isn't here</h1>
        <p style="color:var(--muted);margin:0 0 26px">The link may be out of date. The
           blog index and the services list are both good places to pick the thread up.</p>
        <p><a class="btn btn-primary" href="/">Home</a>
           <a class="btn btn-ghost" href="/blog/" style="margin-left:8px">Blog</a></p>
      </div>
    </section>"""
    return layout(title=f'Page not found — {SITE["name"]}',
                  description="Page not found.", path="/404", body=body)


def render_feed() -> str:
    items = []
    for p in POSTS:
        stamp = format_datetime(dt.datetime.fromisoformat(p["date"] + "T12:00:00+00:00"))
        link = f'{BASE}/blog/{p["slug"]}/'
        items.append(f"""    <item>
      <title>{e(p["title"])}</title>
      <link>{link}</link>
      <guid isPermaLink="true">{link}</guid>
      <pubDate>{stamp}</pubDate>
      <description>{e(p["excerpt"])}</description>
    </item>""")
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>{e(SITE["name"])} — Blog</title>
    <link>{BASE}/blog/</link>
    <description>Offensive security write-ups from {e(SITE["name"])}.</description>
    <language>en-us</language>
    <atom:link href="{BASE}/feed.xml" rel="self" type="application/rss+xml"/>
{chr(10).join(items)}
  </channel>
</rss>
"""


def legacy_stub(old_path: str, new_path: str) -> str:
    """GitHub Pages cannot issue redirects, so old WordPress URLs get a stub page
    that refreshes and declares the canonical. Not as good as a 301, but it keeps
    existing links and bookmarks working."""
    target = BASE + new_path
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Moved — {e(SITE["name"])}</title>
  <link rel="canonical" href="{target}">
  <meta name="robots" content="noindex, follow">
  <meta http-equiv="refresh" content="0; url={target}">
  <script>location.replace({json.dumps(target)});</script>
</head>
<body style="font-family:system-ui,sans-serif;padding:40px">
  <p>This page has moved to <a href="{target}">{target}</a>.</p>
</body>
</html>
"""


FAVICON = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <rect width="64" height="64" rx="8" fill="#0f1b2d"/>
  <circle cx="32" cy="32" r="17" fill="none" stroke="#e8edf5" stroke-width="3"/>
  <path d="M15 32h34M32 15c8 9 8 25 0 34-8-9-8-25 0-34" fill="none" stroke="#e8edf5" stroke-width="2.4"/>
  <circle cx="32" cy="32" r="5.5" fill="#c2352c"/>
</svg>
"""

PAGES = json.loads((CONTENT / "pages.json").read_text(encoding="utf-8"))
POSTS = json.loads((CONTENT / "posts.json").read_text(encoding="utf-8"))
HOME = json.loads((CONTENT / "home.json").read_text(encoding="utf-8"))


def build():
    if DIST.exists():
        shutil.rmtree(DIST)
    shutil.copytree(STATIC, DIST)
    write(DIST / "img" / "favicon.svg", FAVICON)

    write(DIST / "index.html", render_home())
    for pg in PAGES:
        write(DIST / pg["route"].strip("/") / "index.html", render_page(pg))

    for p in POSTS:
        write(DIST / "blog" / p["slug"] / "index.html", render_post(p))
    write(DIST / "blog" / "index.html", render_blog_index())

    write(DIST / "404.html", render_404())
    write(DIST / "feed.xml", render_feed())

    # Old WordPress URLs -> new locations.
    stubs = 0
    for pg in PAGES:
        if pg["legacy_path"].strip("/") != pg["route"].strip("/"):
            write(DIST / pg["legacy_path"].strip("/") / "index.html",
                  legacy_stub(pg["legacy_path"], pg["route"]))
            stubs += 1
    for p in POSTS:
        write(DIST / p["legacy_path"].strip("/") / "index.html",
              legacy_stub(p["legacy_path"], f'/blog/{p["slug"]}/'))
        stubs += 1

    urls = ["/"] + [pg["route"] for pg in PAGES] + ["/blog/"] + [f'/blog/{p["slug"]}/' for p in POSTS]
    body = "\n".join(f"  <url><loc>{BASE}{u}</loc></url>" for u in urls)
    write(DIST / "sitemap.xml",
          '<?xml version="1.0" encoding="UTF-8"?>\n'
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
          f"{body}\n</urlset>\n")
    write(DIST / "robots.txt", f"User-agent: *\nAllow: /\n\nSitemap: {BASE}/sitemap.xml\n")

    write(DIST / "CNAME", "globetech.biz\n")
    write(DIST / ".nojekyll", "")

    print(f"Built -> {DIST}")
    print(f"  {len(PAGES)} pages, {len(POSTS)} posts, {stubs} legacy redirect stubs")


if __name__ == "__main__":
    build()
