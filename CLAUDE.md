# GlobeTech LLC — site guide for Claude

Static site for **globetech.biz**. Vulnerability assessments and penetration
testing, Wisconsin. This is a **real trading business site** — treat changes here
with more care than a hobby project.

Migrated from WordPress 7.0.4 on EC2.

## The one thing to know

Content lives in `content/`. Edit it, run the build, commit.

```bash
python3 build.py     # content/ + static/  ->  dist/
```

Pure standard library. `dist/` is gitignored — GitHub Actions builds on push.

## Where content lives

| What | Where |
|---|---|
| Page bodies (HTML fragments) | `content/pages/SLUG.html` |
| Page titles, routes, nav flags | `content/pages.json` |
| Post bodies (HTML fragments) | `content/posts/SLUG.html` |
| Post metadata, newest first | `content/posts.json` |
| Name, description, email, chat config | `content/site.json` |

Bodies are **HTML, not Markdown** — they were imported from WordPress and kept as
rendered HTML so nothing was lost in translation. `build.py` wraps them in the
layout; it does not rewrite them. Styling for imported markup lives under
`.prose` in the stylesheet.

`tools/ingest_wordpress.py` performed the one-time import. It is kept so the
import is reproducible and its decisions are visible. **Do not re-run it against
the live WordPress site once that site is gone.**

## URLs — read before renaming anything

The WordPress site used ugly permalinks: `/index.php/2020/05/12/oscp-review/`.
The new site uses clean ones: `/blog/oscp-review/`.

GitHub Pages cannot issue redirects, so `build.py` writes a **meta-refresh stub**
at every old path, carrying `rel=canonical` and `noindex`. That is what
`legacy_path` in `posts.json` / `pages.json` is for. 21 stubs exist.

**Never delete a `legacy_path` value** — it is the only thing keeping old links
and search results working. New posts get an empty `legacy_path`.

## The 3CX live chat

The contact page carries `<call-us-selector>` plus `/js/callus.js`. This was
verified to be a self-contained Vue web component with **no WordPress
dependency**: it reads `phonesystem-url` and `party` off the element and talks
only to the 3CX cloud instance.

Two deliberate choices:

- **It loads on the contact page only.** The bundle is 693 KB and the chat is
  nearly never used, so site-wide loading would be poor value.
- **The script is vendored** into `static/js/`. 3CX does not publish a working
  CDN URL for it. That means it will not receive updates — if the widget ever
  breaks, re-download it from a 3CX-provided embed snippet rather than debugging
  the vendored copy.

## Images and media

- `static/img/posts/` — 108 images imported from WordPress, capped at 1600px and
  stripped of metadata by `tools/prepare_images.py`.
- `static/media/` — two `.webm` screencasts and three PowerPoint decks linked
  from posts.

**`2025-06-ReturnOfAMSI.pptx` is 60 MB.** GitHub warns above 50 MB per file (and
blocks above 100 MB). It pushes fine but sits in git history permanently. If it
ever needs to go, replace the link in
`content/posts/the-return-of-amsi-easy-dll-patching-without-c3.html`.

Screenshots stay PNG on purpose — re-encoding terminal output as JPEG puts
ringing artefacts around the text.

23 post images used to point at `http://3.134.223.139`, a decommissioned server,
and had been broken on the live site for some time. The importer repaired them
from the current host. **Do not reintroduce absolute URLs to either old host.**

## Design

Deliberately **not** the dark terminal-green look every pentest firm uses — this
sells assessments to Wisconsin businesses, and reads as a professional services
firm rather than a hacker aesthetic.

- paper `#fbfaf8` · ink `#131820` · navy `#0f1b2d` · signal red `#c2352c`

Signal red is used the way a findings report uses it: sparingly, and only where
it means something. Do not spread it across backgrounds.

There is a full dark-mode palette under `prefers-color-scheme: dark` — this
audience runs dark. If you add a colour, add it to both blocks.

Type is **IBM Plex** (Sans + Mono), self-hosted, chosen because it was drawn for
technical documentation and these posts are full of code and terminal output.

## Deployment

GitHub Pages via `.github/workflows/deploy.yml`. **The repo must stay public** —
Pages on the Free plan cannot publish from a private repo.

Apex is canonical here (`www` → `globetech.biz`), which is the opposite of the
teekaudio.com site. `dist/CNAME` must keep saying `globetech.biz`.

DNS lives in Microsoft 365 and **stays there**. M365 has no API for arbitrary DNS
records, so they are edited by hand:

```
A     @     185.199.108.153 / .109.153 / .110.153 / .111.153
CNAME www   galoryber.github.io
```

Mail records — MX, SPF (which includes `zohosign.com` and `sender.zohoinvoice.com`
for invoicing and e-signature), autodiscover — are untouched by any of this and
must stay that way.

## Gotchas

- **Blog comments are gone.** WordPress handled them; a static site cannot. This
  was an accepted loss, not an oversight.
- `/feed.xml` is new. The old site's `/feed/` 404'd, so no existing subscriber
  was broken.
- The old site had no DMARC record. Still true, still worth raising, still
  outside the scope of this repo.
