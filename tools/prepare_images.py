#!/usr/bin/env python3
"""
Downsize and strip metadata from imported post images, in place.

The WordPress originals totalled 79 MB — full-resolution uploads, most of them
screenshots displayed at a fraction of their size. This caps them at a sensible
width and removes metadata.

    .venv/bin/python tools/prepare_images.py

Screenshots stay PNG. Re-encoding a screenshot as JPEG puts ringing artefacts
around text, which matters when the text is a terminal session or a debugger.
Photographs stay JPEG. Nothing is ever upscaled.
"""

import os
import sys
from pathlib import Path

try:
    from PIL import Image, ImageOps
except ImportError:
    sys.exit("Pillow not found: python3 -m venv .venv && .venv/bin/pip install Pillow")

ROOT = Path(__file__).resolve().parent.parent
TARGETS = [ROOT / "static" / "img" / "posts"]
MAX_W = 1600
JPEG_QUALITY = 84


def main():
    before = after = 0
    changed = 0
    for d in TARGETS:
        for f in sorted(d.iterdir()):
            if f.suffix.lower() not in (".png", ".jpg", ".jpeg", ".gif", ".webp"):
                continue
            size_before = f.stat().st_size
            before += size_before
            if f.suffix.lower() == ".gif":          # may be animated; leave alone
                after += size_before
                continue
            with Image.open(f) as im:
                im = ImageOps.exif_transpose(im)
                is_png = f.suffix.lower() == ".png"
                if im.width > MAX_W:
                    im.thumbnail((MAX_W, MAX_W * 4), Image.LANCZOS)
                im.info.pop("exif", None)
                if is_png:
                    if im.mode not in ("RGB", "RGBA", "P", "L"):
                        im = im.convert("RGBA")
                    im.save(f, "PNG", optimize=True)
                else:
                    if im.mode not in ("RGB", "L"):
                        im = im.convert("RGB")
                    im.save(f, "JPEG", quality=JPEG_QUALITY, optimize=True,
                            progressive=True, exif=b"")
            size_after = f.stat().st_size
            after += size_after
            if size_after != size_before:
                changed += 1
    print(f"  {changed} images rewritten")
    print(f"  {before/1e6:.1f} MB -> {after/1e6:.1f} MB "
          f"({100 - after/before*100:.0f}% smaller)")


if __name__ == "__main__":
    main()
