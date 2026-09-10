# globetech.biz

Static site for **GlobeTech LLC** — vulnerability assessments and penetration
testing, Wisconsin.

Migrated from WordPress. Built from imported HTML by a dependency-free Python
script; hosted on GitHub Pages.

## Build

```bash
python3 build.py
```

Requires Python 3.9+. Nothing to install.

Preview locally:

```bash
python3 build.py && python3 -m http.server 8000 --directory dist
```

## Editing

| What | Where |
|---|---|
| Business name, description, contact, chat config | `content/site.json` |
| Page bodies | `content/pages/SLUG.html` |
| Page titles, routes, nav | `content/pages.json` |
| Blog post bodies | `content/posts/SLUG.html` |
| Post titles, dates, excerpts | `content/posts.json` |
| Colours and type | top of `static/css/site.css` |

Push to `main`; GitHub Actions builds and deploys. `dist/` is not committed.

## Adding a blog post

1. Write the body as an HTML fragment in `content/posts/my-slug.html`
   (no `<html>`/`<body>` — just the content).
2. Add an entry at the top of `content/posts.json`:

```json
{
  "slug": "my-slug",
  "title": "My title",
  "date": "2026-09-09",
  "excerpt": "One or two sentences for the index and the RSS feed.",
  "legacy_path": ""
}
```

`legacy_path` is only for posts that existed on the old WordPress site — leave it
empty for new ones.

## Deployment

GitHub Pages via `.github/workflows/deploy.yml`. The repository must stay public.

DNS stays in Microsoft 365. Only these point here:

```
A     @     185.199.108.153, 185.199.109.153, 185.199.110.153, 185.199.111.153
CNAME www   galoryber.github.io
```

Mail records (MX, SPF including the Zoho includes, autodiscover) are untouched.
