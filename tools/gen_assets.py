#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Art for the Gunian7 profile README — restrained editorial noir.

Only two assets, both deliberately quiet:
  assets/banner.png  — charcoal gradient plate with the name set in Georgia
  assets/rule.svg    — hairline + single crimson dot used as a section rule

Everything else on the profile is real markdown text (tables, lists, badges) so it
stays readable, selectable, searchable and mobile-friendly.
Run from the repo root:  python tools/gen_assets.py
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
ASSETS.mkdir(exist_ok=True)

FONTS = Path("C:/Windows/Fonts")
SERIF = FONTS / "georgia.ttf"
SERIF_B = FONTS / "georgiab.ttf"
MONO = FONTS / "consola.ttf"

PAPER = (238, 235, 229)
BLOOD = (179, 18, 27)


def font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), size)


def vgrad(size, stops):
    w, h = size
    col = Image.new("RGB", (1, h))
    d = ImageDraw.Draw(col)
    stops = sorted(stops)
    for y in range(h):
        t = y / max(h - 1, 1)
        c = stops[-1][1]
        for i in range(len(stops) - 1):
            p0, c0 = stops[i]
            p1, c1 = stops[i + 1]
            if p0 <= t <= p1:
                k = 0 if p1 == p0 else (t - p0) / (p1 - p0)
                c = tuple(int(c0[j] + (c1[j] - c0[j]) * k) for j in range(3))
                break
        d.point((0, y), c)
    return col.resize((w, h), Image.BILINEAR)


def tracked(draw, xy, text, fnt, fill, tracking=0.0):
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=fnt, fill=fill)
        x += draw.textlength(ch, font=fnt) + tracking
    return x


def soft_glow(img, cx, cy, radius, color, strength=0.5):
    """One restrained light source: a wide, very low-opacity radial wash."""
    w, h = img.size
    small = 160
    m = Image.new("L", (small, small), 0)
    px = m.load()
    scx, scy = cx / w * small, cy / h * small
    sr = radius / w * small
    for y in range(small):
        for x in range(small):
            r = ((x - scx) ** 2 + (y - scy) ** 2) ** 0.5 / max(sr, 1e-6)
            px[x, y] = 0 if r >= 1 else int(255 * (1 - r) ** 2)
    m = m.resize((w, h), Image.BICUBIC).filter(ImageFilter.GaussianBlur(40))
    layer = Image.new("RGB", (w, h), color)
    return ImageChops.screen(
        img, Image.composite(layer, Image.new("RGB", (w, h)), m.point(lambda v: int(v * strength)))
    )


def build_banner(w=1600, h=400):
    img = vgrad((w, h), [(0.0, (17, 18, 21)), (0.55, (23, 24, 28)), (1.0, (14, 15, 18))])

    # a single warm key light in the upper right, well out of the type area
    img = soft_glow(img, w * 0.82, h * 0.18, 620, (58, 54, 50), 0.55)
    # and a whisper of crimson on the far edge
    img = soft_glow(img, w * 0.99, h * 0.9, 420, (74, 8, 12), 0.5)

    # one very light grain pass so the gradient never bands
    noise = Image.effect_noise((w, h), 12).convert("RGB")
    img = Image.blend(img, ImageChops.overlay(img, noise), 0.10)

    d = ImageDraw.Draw(img)
    left, top = 104, 92

    # hairline + crimson tick above the name
    d.rectangle([left, top, left + 84, top + 3], fill=BLOOD)

    tracked(d, (left, top + 34), "WEIKAI CHEN", font(MONO, 17), (126, 126, 136), 4.2)

    d.text((left - 4, top + 62), "Gunian7", font=font(SERIF_B, 104), fill=PAPER)

    d.text(
        (left, top + 194),
        "Robotics · Computer Vision · Full-Stack",
        font=font(SERIF, 30),
        fill=(198, 195, 189),
    )
    tracked(
        d,
        (left, top + 242),
        "HDU PHOENIX VISION GROUP  ·  HANGZHOU DIANZI UNIVERSITY",
        font(MONO, 16),
        (154, 154, 164),
        2.4,
    )

    out = ASSETS / "banner.png"
    img.save(out, optimize=True)
    return out, img.size


def rule_svg(w=1600, h=48):
    body = (
        f'  <line x1="0" y1="{h//2}" x2="{w//2 - 40}" y2="{h//2}" stroke="#2A2B31" stroke-width="1"/>\n'
        f'  <circle cx="{w//2}" cy="{h//2}" r="4" fill="#B3121B"/>\n'
        f'  <line x1="{w//2 + 40}" y1="{h//2}" x2="{w}" y2="{h//2}" stroke="#2A2B31" stroke-width="1"/>'
    )
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img">\n{body}\n</svg>\n'
    )
    out = ASSETS / "rule.svg"
    out.write_text(svg, encoding="utf-8")
    return out, (w, h)


def main():
    banner, bsize = build_banner()
    rule, rsize = rule_svg()
    print(f"{banner.name:14s} {bsize[0]}x{bsize[1]}  {banner.stat().st_size/1024:6.1f} KB")
    print(f"{rule.name:14s} {rsize[0]}x{rsize[1]}  {rule.stat().st_size/1024:6.1f} KB")


if __name__ == "__main__":
    main()
