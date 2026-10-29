#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate the noir film art assets for the Gunian7 profile README.

Everything here is drawn procedurally (PIL) or hand-written SVG, so the art is
reproducible and lives in the repo instead of depending on a third-party badge
service. Run from the repo root:  python tools/gen_assets.py
"""
from __future__ import annotations

import math
import random
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps
from PIL import ImageEnhance, ImageStat

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
ASSETS.mkdir(exist_ok=True)

FONTS = Path("C:/Windows/Fonts")
SERIF = FONTS / "georgiab.ttf"
SERIF_R = FONTS / "georgia.ttf"
SERIF_I = FONTS / "georgiai.ttf"
MONO = FONTS / "consola.ttf"
MONO_B = FONTS / "consolab.ttf"

INK = (8, 8, 10)
PAPER = (243, 241, 236)
BLOOD = (179, 18, 27)
ASH = (154, 154, 164)


def font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), size)


def hgrad(size, top, bottom):
    """Vertical gradient image."""
    w, h = size
    img = Image.new("RGB", (1, h))
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / max(h - 1, 1)
        d.point((0, y), tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)))
    return img.resize((w, h), Image.BILINEAR)


def hgrad3(size, stops):
    """Vertical gradient through (position 0..1, colour) stops — no seams."""
    w, h = size
    img = Image.new("RGB", (1, h))
    d = ImageDraw.Draw(img)
    stops = sorted(stops, key=lambda s: s[0])
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
    return img.resize((w, h), Image.BILINEAR)


def radial_mask(size, cx, cy, rx, ry, power=2.0, invert=False):
    """Soft radial falloff mask (L)."""
    w, h = size
    small = 160
    m = Image.new("L", (small, small), 0)
    px = m.load()
    scx, scy = cx / w * small, cy / h * small
    srx, sry = max(rx / w * small, 0.001), max(ry / h * small, 0.001)
    for y in range(small):
        for x in range(small):
            dx = (x - scx) / srx
            dy = (y - scy) / sry
            r = math.hypot(dx, dy)
            v = 0.0 if r >= 1 else (1.0 - r) ** power
            px[x, y] = int(255 * (1 - v if invert else v))
    return m.resize((w, h), Image.BICUBIC).filter(ImageFilter.GaussianBlur(max(w, h) / 400))


def screen_glow(base, mask, color, strength=1.0):
    """Additive coloured glow through a mask."""
    layer = Image.new("RGB", base.size, color)
    scaled = mask.point(lambda v, s=strength: min(255, int(v * s)))
    return Image.composite(ImageChops.screen(base, layer), base, scaled)


def add_grain(img, sigma=26, amount=0.34):
    noise = Image.effect_noise(img.size, sigma).convert("RGB")
    return Image.blend(img, ImageChops.overlay(img, noise), amount)


def add_vignette(img, strength=0.85, power=2.2):
    w, h = img.size
    mask = radial_mask(img.size, w / 2, h / 2, w * 0.78, h * 0.86, power=power)
    dark = Image.new("RGB", img.size, (0, 0, 0))
    return Image.composite(img, dark, mask.point(lambda v: 255 - int((255 - v) * strength)))


def draw_tracked(draw, xy, text, fnt, fill, tracking=0, anchor_left=True):
    """Letter-spaced text."""
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=fnt, fill=fill)
        x += draw.textlength(ch, font=fnt) + tracking
    return x


def wipe_noise_edges(img, box, radius=6):
    """Blur the inside of a rectangle to fake depth-of-field."""
    x0, y0, x1, y1 = box
    region = img.crop(box).filter(ImageFilter.GaussianBlur(radius))
    img.paste(region, (x0, y0))
    return img


# --------------------------------------------------------------------------
# 1. Banner: rainy noir street, hard light, one blood-red neon
# --------------------------------------------------------------------------
def build_banner(w=1600, h=560, seed=11):
    rnd = random.Random(seed)
    horizon = int(h * 0.62)
    # one continuous gradient for sky + wet street: no horizon seam
    img = hgrad3(
        (w, h),
        [
            (0.0, (5, 5, 8)),
            (0.45, (11, 11, 15)),
            (0.62, (19, 19, 24)),
            (0.72, (12, 12, 16)),
            (1.0, (6, 6, 9)),
        ],
    )

    # city skyline silhouette
    layer = Image.new("RGB", (w, h), (0, 0, 0))
    d = ImageDraw.Draw(layer)
    base_col = (12, 12, 16)
    x = -40
    while x < w + 40:
        bw = rnd.randint(46, 130)
        bh = rnd.randint(int(h * 0.14), int(h * 0.40))
        top = horizon - bh
        shade = rnd.choice([(10, 10, 13), (13, 13, 17), (16, 16, 21)])
        d.rectangle([x, top, x + bw, horizon], fill=shade)
        if rnd.random() < 0.5:
            d.rectangle([x + bw // 2 - 6, top - rnd.randint(8, 26), x + bw // 2 + 6, top], fill=shade)
        # roof furniture so silhouettes read as buildings, not flat blocks
        if rnd.random() < 0.7:
            tw = rnd.randint(14, 30)
            tx = x + rnd.randint(8, max(9, bw - tw - 4))
            d.rectangle([tx, top - rnd.randint(14, 34), tx + tw, top], fill=shade)
        if rnd.random() < 0.45:  # water tank on legs
            tx = x + rnd.randint(10, max(11, bw - 30))
            d.rectangle([tx, top - 22, tx + 18, top - 8], fill=shade)
            d.rectangle([tx + 2, top - 8, tx + 4, top], fill=shade)
            d.rectangle([tx + 14, top - 8, tx + 16, top], fill=shade)
        # faint rim light on the roof edge so the skyline separates from the sky
        d.line([x, top, x + bw, top], fill=tuple(min(255, c + 16) for c in shade), width=1)
        for _ in range(rnd.randint(0, 9)):  # sparse lit windows
            wx = x + rnd.randint(6, max(7, bw - 12))
            wy = top + rnd.randint(10, max(11, bh - 14))
            d.rectangle([wx, wy, wx + 3, wy + 4], fill=rnd.choice([(86, 78, 58), (104, 90, 62), (56, 62, 74)]))
        x += bw + rnd.randint(2, 16)
    img = Image.composite(layer, img, layer.convert("L").point(lambda v: 255 if v > 4 else 0))

    overlay = Image.new("RGB", (w, h), (0, 0, 0))
    od = ImageDraw.Draw(overlay)

    # street lamp + cone
    lamp_x, lamp_y = int(w * 0.74), horizon - 150
    od.rectangle([lamp_x - 2, lamp_y, lamp_x + 2, horizon], fill=(26, 26, 32))
    od.rectangle([lamp_x - 16, lamp_y - 8, lamp_x + 16, lamp_y], fill=(74, 70, 58))
    cone = [(lamp_x - 14, lamp_y), (lamp_x + 14, lamp_y), (lamp_x + 150, h), (lamp_x - 150, h)]
    cone_mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(cone_mask).polygon(cone, fill=90)
    cone_mask = cone_mask.filter(ImageFilter.GaussianBlur(90)).point(lambda v: int(v * 0.55))

    img = screen_glow(img, radial_mask((w, h), lamp_x, lamp_y, 170, 170, 2.8), (255, 238, 205), 0.52)
    img = Image.composite(
        ImageChops.screen(img, Image.new("RGB", (w, h), (58, 54, 44))), img, cone_mask
    )

    # blood-red neon blade sign bolted to a wall: tube strokes + bracket + bloom
    neon_x, neon_y = int(w * 0.885), int(horizon - 196)
    tube = Image.new("RGB", (w, h), (0, 0, 0))
    nd = ImageDraw.Draw(tube)
    blade_w, blade_h = 66, 186
    bx0, by0 = neon_x - blade_w // 2, neon_y
    bx1, by1 = bx0 + blade_w, by0 + blade_h
    wall_x = bx0 - 46
    nd.rectangle([wall_x - 8, by0 - 40, wall_x, by1 + 26], fill=(19, 19, 24))  # wall the sign hangs on
    # bracket back to the wall
    nd.line([bx0, by0 + 18, wall_x, by0 - 14], fill=(96, 96, 104), width=5)
    nd.line([bx0, by1 - 18, wall_x, by1 + 10], fill=(96, 96, 104), width=5)
    # sign body: dark panel + neon tube outline
    nd.rounded_rectangle([bx0, by0, bx1, by1], radius=5, fill=(22, 5, 7))
    nd.rounded_rectangle([bx0 + 6, by0 + 6, bx1 - 6, by1 - 6], radius=4, outline=(224, 32, 38), width=5)
    for i in range(3):  # three glowing tube bars, like a late-night bar sign
        yy = by0 + 44 + i * 44
        nd.line([bx0 + 19, yy, bx1 - 19, yy], fill=(238, 44, 50), width=6)
    nd.line([bx0 + 19, by0 + 24, bx1 - 19, by0 + 24], fill=(230, 40, 46), width=5)
    nd.line([bx0 + 19, by1 - 26, bx1 - 19, by1 - 26], fill=(180, 22, 28), width=4)
    img = ImageChops.add(img, tube)
    # bloom: the light spills onto the wet air
    img = screen_glow(img, tube.filter(ImageFilter.GaussianBlur(30)).convert("L"), (90, 0, 6), 1.0)
    img = screen_glow(img, tube.filter(ImageFilter.GaussianBlur(9)).convert("L"), (110, 6, 8), 1.0)
    img = screen_glow(img, radial_mask((w, h), neon_x, neon_y + blade_h // 2, 300, 300, 1.9), (128, 14, 18), 1.0)

    # reflections on the wet street
    refl = Image.new("RGB", (w, h), (0, 0, 0))
    rd = ImageDraw.Draw(refl)
    for sx, col, spread in ((lamp_x, (96, 88, 70), 120), (neon_x, (110, 14, 20), 90)):
        for _ in range(90):
            rx = sx + int(rnd.gauss(0, spread * 0.42))
            ry = rnd.randint(horizon + 2, h)
            ln = int(abs(rnd.gauss(0, 22)) + 2)
            alpha_layer = rnd.randint(24, 66)
            rd.line([rx, ry, rx, min(h, ry + ln)], fill=tuple(int(c * alpha_layer / 255) for c in col), width=rnd.choice([1, 1, 2]))
    refl = refl.filter(ImageFilter.GaussianBlur(1.4))
    img = ImageChops.add(img, refl)

    # rain
    rain = Image.new("RGB", (w, h), (0, 0, 0))
    rdraw = ImageDraw.Draw(rain)
    for _ in range(520):
        x0 = rnd.randint(-80, w)
        y0 = rnd.randint(-40, h)
        ln = rnd.randint(18, 70)
        dx = -ln * 0.22
        a = rnd.randint(26, 78)
        rdraw.line([x0, y0, x0 + dx, y0 + ln], fill=(int(200 * a / 255), int(210 * a / 255), int(225 * a / 255)), width=1)
    img = ImageChops.add(img, rain.filter(ImageFilter.GaussianBlur(0.7)))

    # the sign must light the scene: red-tinted rain and a wet wall smear in front of it
    spill = radial_mask((w, h), neon_x, neon_y + blade_h // 2, 300, 320, 1.7)
    red_rain = Image.new("RGB", (w, h), (0, 0, 0))
    rrd = ImageDraw.Draw(red_rain)
    for _ in range(320):
        ang = rnd.uniform(0, 6.283)
        dist = rnd.uniform(0, 300)
        x0 = int(neon_x + math.cos(ang) * dist)
        y0 = int(neon_y + blade_h // 2 + math.sin(ang) * dist * 1.1)
        ln = rnd.randint(16, 54)
        a = rnd.randint(60, 150)
        rrd.line([x0, y0, x0 - ln * 0.22, y0 + ln], fill=(min(255, int(220 * a / 255)), int(30 * a / 255), int(32 * a / 255)), width=1)
    img = ImageChops.add(img, Image.composite(red_rain, Image.new("RGB", (w, h)), spill))
    img = screen_glow(
        img,
        radial_mask((w, h), wall_x + 4, by0 + blade_h // 2, 120, 240, 1.5),
        (96, 8, 10),
        1.0,
    )

    # hard light shaft from upper left
    shaft = Image.new("L", (w, h), 0)
    ImageDraw.Draw(shaft).polygon([(0, 0), (int(w * 0.26), 0), (int(w * 0.52), h), (int(w * 0.16), h)], fill=255)
    shaft = shaft.filter(ImageFilter.GaussianBlur(60)).point(lambda v: int(v * 0.20))
    img = ImageChops.screen(img, Image.composite(Image.new("RGB", (w, h), (120, 126, 140)), Image.new("RGB", (w, h)), shaft))

    # film scratches
    scratch = Image.new("RGB", (w, h), (0, 0, 0))
    sdraw = ImageDraw.Draw(scratch)
    for _ in range(7):
        sx = rnd.randint(0, w)
        sdraw.line([sx, 0, sx + rnd.randint(-6, 6), h], fill=(28, 28, 32), width=1)
    img = ImageChops.add(img, scratch)

    img = add_grain(img, sigma=24, amount=0.30)
    img = add_vignette(img, strength=0.9, power=2.0)

    # typography
    d = ImageDraw.Draw(img)
    left = 96
    d.line([left - 26, 150, left - 26, 402], fill=BLOOD, width=3)

    f_kick = font(MONO, 19)
    draw_tracked(d, (left, 146), "CASE FILE 07  /  OPERATOR DOSSIER", f_kick, (176, 176, 186), 3.4)

    f_title = font(SERIF, 112)
    title = "GUNIAN7"
    # soft shadow
    shadow = Image.new("RGB", (w, h), (0, 0, 0))
    draw_tracked(ImageDraw.Draw(shadow), (left + 5, 197), title, f_title, (16, 16, 20), 8)
    img = ImageChops.add(img, shadow.filter(ImageFilter.GaussianBlur(10)))
    d = ImageDraw.Draw(img)
    draw_tracked(d, (left, 192), title, f_title, PAPER, 8)

    d.rectangle([left, 330, left + 250, 333], fill=BLOOD)
    f_sub = font(MONO_B, 26)
    draw_tracked(d, (left, 352), "LOTUS  ·  NOIR UNIT", f_sub, (228, 224, 216), 4.5)
    f_small = font(MONO, 19)
    draw_tracked(d, (left, 400), "ROBOTICS · COMPUTER VISION · FULL-STACK", f_small, (186, 186, 196), 2.6)

    draw_tracked(d, (left, h - 64), "35MM  /  2026  /  HANGZHOU", font(MONO, 17), (150, 150, 160), 2.4)

    # film-strip perforations top & bottom
    img = add_film_edges(img)
    out = ASSETS / "noir-banner.png"
    img.save(out, optimize=True)
    return out, img.size


def add_film_edges(img, bar=26):
    w, h = img.size
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, w, bar], fill=(4, 4, 6))
    d.rectangle([0, h - bar, w, h], fill=(4, 4, 6))
    hole_w, hole_h, gap = 26, 14, 24
    x = gap
    while x < w - gap:
        d.rounded_rectangle([x, 6, x + hole_w, 6 + hole_h], radius=3, fill=(46, 46, 54), outline=(70, 70, 80), width=1)
        d.rounded_rectangle([x, h - bar + 6, x + hole_w, h - bar + 6 + hole_h], radius=3, fill=(46, 46, 54), outline=(70, 70, 80), width=1)
        x += hole_w + gap
    return img


# --------------------------------------------------------------------------
# 2. Portrait: the Noir character as a printed noir still
# --------------------------------------------------------------------------
def build_portrait(src: Path, out_w=660, out_h=880, seed=5):
    im = Image.open(src).convert("RGB")
    W, H = im.size
    # solid threshold: the sheet's background is pure black, so ignore noise/watermarks
    bbox = im.convert("L").point(lambda v: 255 if v > 40 else 0).getbbox() or (0, 0, W, H)
    l, t, r, b = bbox
    cw = max(1, r - l)
    # bust framing: head and torso fill the frame so the face actually reads
    crop_w = int(cw * 0.62)
    crop_h = int(crop_w * out_h / out_w)
    cx = (l + r) // 2
    x0 = max(0, cx - crop_w // 2 - int(crop_w * 0.05))
    y0 = max(0, t - int(crop_w * 0.03))
    box = (x0, y0, min(W, x0 + crop_w), min(H, y0 + crop_h))
    im = im.crop(box)

    canvas = Image.new("RGB", (out_w, out_h), (5, 5, 7))
    scaled = im.resize((out_w, max(1, int(im.size[1] * out_w / im.size[0]))), Image.LANCZOS)
    canvas.paste(scaled.filter(ImageFilter.UnsharpMask(radius=2, percent=55, threshold=2)), (0, 0))

    # duotone print with a proper S-curve so the middle tones separate
    gray = ImageOps.autocontrast(canvas.convert("L"), cutoff=0.2)
    # gentle S-curve with a lifted midtone so the face never sinks into the black
    curve = [int(255 * (0.5 - 0.5 * math.cos(math.pi * ((v / 255) ** 1.12)))) for v in range(256)]
    curve = [min(255, int(c * 0.9 + 14)) for c in curve]
    gray = gray.point(curve)
    duotone = ImageOps.colorize(gray, black=(6, 6, 8), mid=(124, 124, 134), white=(243, 240, 233))
    duotone = duotone.convert("RGB")

    # auto exposure: normalise the crop to a fixed mean so the figure always reads
    mean = ImageStat.Stat(duotone.convert("L")).mean[0] or 1
    duotone = ImageEnhance.Brightness(duotone).enhance(min(3.2, max(1.0, 54.0 / mean)))

    # hard key light from upper left: lift the lit side of the frame
    key = radial_mask((out_w, out_h), out_w * 0.24, out_h * 0.20, out_w * 0.98, out_h * 0.95, 1.3)
    duotone = ImageChops.screen(
        duotone,
        Image.composite(
            Image.new("RGB", (out_w, out_h), (44, 42, 40)),
            Image.new("RGB", (out_w, out_h)),
            key.point(lambda v: int(v * 0.5)),
        ),
    )
    # blood-red rim light along the subject edge
    rim = radial_mask((out_w, out_h), out_w * 0.16, out_h * 0.30, out_w * 0.40, out_h * 0.36, 2.4)
    duotone = screen_glow(duotone, rim.point(lambda v: int(v * 0.6)), (104, 12, 18), 1.0)

    # dodge + contrast the face so the eyes are the first thing you see
    face = radial_mask((out_w, out_h), out_w * 0.40, out_h * 0.17, out_w * 0.26, out_h * 0.17, 1.5)
    lifted = ImageEnhance.Contrast(duotone).enhance(1.32)
    lifted = ImageChops.screen(
        lifted,
        Image.composite(
            Image.new("RGB", (out_w, out_h), (34, 34, 36)),
            Image.new("RGB", (out_w, out_h)),
            face.point(lambda v: int(v * 0.75)),
        ),
    )
    duotone = Image.composite(lifted, duotone, face)

    # picture area
    rnd = random.Random(seed)

    # scanlines / print grid
    lines = Image.new("RGB", (out_w, out_h), (0, 0, 0))
    ld = ImageDraw.Draw(lines)
    for y in range(0, out_h, 4):
        ld.line([0, y, out_w, y], fill=(7, 7, 9), width=1)
    duotone = ImageChops.add(duotone, lines)

    img = add_grain(duotone, sigma=30, amount=0.42)
    img = add_vignette(img, strength=0.72, power=1.9)

    d = ImageDraw.Draw(img)
    # frame
    d.rectangle([10, 10, out_w - 11, out_h - 11], outline=(28, 28, 34), width=1)

    # caption plate
    plate_h = 112
    plate = Image.new("RGBA", (out_w, plate_h), (6, 6, 8, 232))
    img.paste(Image.alpha_composite(img.crop((0, out_h - plate_h, out_w, out_h)).convert("RGBA"), plate).convert("RGB"), (0, out_h - plate_h))
    d = ImageDraw.Draw(img)
    d.line([0, out_h - plate_h, out_w, out_h - plate_h], fill=(38, 38, 46), width=1)
    d.line([30, out_h - 80, 110, out_h - 80], fill=BLOOD, width=3)
    draw_tracked(d, (30, out_h - 70), "THE ONLY ONE BY MY SIDE", font(MONO_B, 16), (198, 198, 208), 2.2)
    d.text((30, out_h - 46), "NOIR", font=font(SERIF, 38), fill=PAPER)
    draw_tracked(d, (out_w - 176, out_h - 40), "SUBJECT / 07", font(MONO, 14), (146, 146, 158), 1.8)

    # corner ticks last so nothing paints over them
    tick = 22
    for (cx0, cy0, dx, dy) in (
        (10, 10, 1, 1),
        (out_w - 11, 10, -1, 1),
        (10, out_h - 11, 1, -1),
        (out_w - 11, out_h - 11, -1, -1),
    ):
        d.line([cx0, cy0, cx0 + dx * tick, cy0], fill=BLOOD, width=2)
        d.line([cx0, cy0, cx0, cy0 + dy * tick], fill=BLOOD, width=2)

    out = ASSETS / "noir-portrait.png"
    img.save(out, optimize=True)
    return out, img.size


# --------------------------------------------------------------------------
# 3. Section strip: rain on glass + red light leak
# --------------------------------------------------------------------------
def build_strip(w=1600, h=170, seed=23):
    rnd = random.Random(seed)
    img = hgrad((w, h), (7, 7, 9), (12, 12, 16))
    bokeh = Image.new("RGB", (w, h), (0, 0, 0))
    bd = ImageDraw.Draw(bokeh)
    for _ in range(26):
        cx, cy = rnd.randint(0, w), rnd.randint(-30, h + 30)
        r = rnd.randint(14, 78)
        a = rnd.randint(10, 40)
        bd.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(a, a, int(a * 1.1)))
    img = ImageChops.add(img, bokeh.filter(ImageFilter.GaussianBlur(16)))

    glass = Image.new("RGB", (w, h), (0, 0, 0))
    gd = ImageDraw.Draw(glass)
    for _ in range(420):
        x0 = rnd.randint(0, w)
        y0 = rnd.randint(-20, h)
        ln = rnd.randint(8, 42)
        a = rnd.randint(20, 66)
        gd.line([x0, y0, x0 + rnd.randint(-3, 3), y0 + ln], fill=(a, a, a), width=rnd.choice([1, 1, 2]))
    img = ImageChops.add(img, glass.filter(ImageFilter.GaussianBlur(1.1)))

    # red light leak on the right
    img = screen_glow(img, radial_mask((w, h), w * 1.02, h * 0.4, w * 0.34, h * 1.6, 1.6), (128, 12, 18), 0.85)
    img = add_grain(img, sigma=22, amount=0.26)
    img = add_vignette(img, strength=0.55, power=1.4)
    d = ImageDraw.Draw(img)
    d.line([0, 0, w, 0], fill=(26, 26, 32), width=1)
    d.line([0, h - 1, w, h - 1], fill=(26, 26, 32), width=1)
    out = ASSETS / "noir-strip.png"
    img.save(out, optimize=True)
    return out, img.size


# --------------------------------------------------------------------------
# 4. Hand-written SVG assets
# --------------------------------------------------------------------------
GRAIN_FILTER = """
    <filter id="grain" x="0" y="0" width="100%" height="100%">
      <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" stitchTiles="stitch"/>
      <feColorMatrix type="saturate" values="0"/>
    </filter>"""

SANS_CN = "'Microsoft YaHei','PingFang SC','Hiragino Sans GB','Noto Sans SC',sans-serif"
SERIF_STACK = "Georgia,'Times New Roman','Songti SC',serif"
MONO_STACK = "Consolas,'SF Mono',Menlo,'DejaVu Sans Mono',monospace"


def svg_open(w, h, body, extra_defs=""):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
        f'role="img">\n  <defs>{GRAIN_FILTER}{extra_defs}</defs>\n{body}\n</svg>\n'
    )


def grain_rect(w, h, opacity=0.05):
    return f'  <rect width="{w}" height="{h}" filter="url(#grain)" opacity="{opacity}"/>\n'


def casefile_svg(w=620, h=620):
    b = []
    b.append(f'<rect width="{w}" height="{h}" fill="#08080A"/>')
    b.append(f'<rect x="0.75" y="0.75" width="{w-1.5}" height="{h-1.5}" fill="none" stroke="#23242B" stroke-width="1.5"/>')
    # corner ticks in blood red
    t = 26
    for (x, y, dx, dy) in ((0, 0, 1, 1), (w, 0, -1, 1), (0, h, 1, -1), (w, h, -1, -1)):
        b.append(f'<path d="M{x} {y + dy*t} L{x} {y} L{x + dx*t} {y}" fill="none" stroke="#B3121B" stroke-width="2.5"/>')
    # fingerprint arcs
    for i, r in enumerate(range(70, 250, 26)):
        b.append(f'<circle cx="{w-58}" cy="{h-92}" r="{r}" fill="none" stroke="#15151A" stroke-width="1.2"/>')
    b.append(f'<text x="40" y="52" font-family="{MONO_STACK}" font-size="12" letter-spacing="3.5" fill="#6C6C74">OPERATOR DOSSIER</text>')
    b.append(f'<text x="{w-40}" y="52" text-anchor="end" font-family="{MONO_STACK}" font-size="12" letter-spacing="2" fill="#B3121B">No. 07-1029</text>')
    b.append(f'<line x1="40" y1="72" x2="{w-40}" y2="72" stroke="#B3121B" stroke-width="2"/>')

    rows = [
        ("NAME", "Weikai Chen", "serif"),
        ("ALIAS", "Gunian7  /  Lotus", "mono"),
        ("UNIT", "HDU PHOENIX · Vision Group", "cn"),
        ("ACADEMY", "Hangzhou Dianzi University", "cn"),
        ("FIELD", "Robotics · Computer Vision · Full-Stack", "mono"),
        ("STATUS", "ALIVE", "alive"),
    ]
    y = 118
    for label, value, kind in rows:
        b.append(f'<text x="40" y="{y}" font-family="{MONO_STACK}" font-size="11" letter-spacing="3" fill="#55555E">{label}</text>')
        if kind == "serif":
            b.append(f'<text x="40" y="{y+38}" font-family="{SERIF_STACK}" font-size="30" fill="#F2F0EB">{escape(value)}</text>')
            y += 76
        elif kind == "alive":
            b.append(f'<text x="40" y="{y+30}" font-family="{MONO_STACK}" font-size="22" font-weight="bold" letter-spacing="4" fill="#B3121B">{value}</text>')
            b.append(f'<circle cx="150" cy="{y+22}" r="4" fill="#B3121B"/>')
            y += 62
        else:
            fam = MONO_STACK if kind == "mono" else SANS_CN
            size = 15 if kind == "mono" else 17
            b.append(f'<text x="40" y="{y+26}" font-family="{fam}" font-size="{size}" fill="#C6C6CC">{escape(value)}</text>')
            y += 56
    # motto block
    b.append(f'<line x1="40" y1="{h-118}" x2="{w-40}" y2="{h-118}" stroke="#1C1C22" stroke-width="1"/>')
    b.append(f'<text x="40" y="{h-88}" font-family="{MONO_STACK}" font-size="11" letter-spacing="3" fill="#55555E">MOTTO</text>')
    b.append(f'<text x="40" y="{h-52}" font-family="{SERIF_STACK}" font-style="italic" font-size="23" fill="#E6E2D9">To have Noir truly by my side.</text>')
    b.append(grain_rect(w, h, 0.045))
    return svg_open(w, h, "\n".join(b))


def divider_svg(label="ACT I", note="", w=1600, h=76):
    b = []
    b.append(f'<rect width="{w}" height="{h}" fill="none"/>')
    cy = h // 2
    b.append(f'<line x1="0" y1="{cy}" x2="{w//2-190}" y2="{cy}" stroke="#22232B" stroke-width="1"/>')
    b.append(f'<line x1="{w//2+190}" y1="{cy}" x2="{w}" y2="{cy}" stroke="#22232B" stroke-width="1"/>')
    b.append(f'<rect x="{w//2-180}" y="{cy-2}" width="360" height="4" fill="#B3121B"/>')
    b.append(f'<text x="{w//2}" y="{cy-14}" text-anchor="middle" font-family="{MONO_STACK}" font-size="15" letter-spacing="7" fill="#8A8A94">{escape(label)}</text>')
    if note:
        b.append(f'<text x="{w//2}" y="{cy+30}" text-anchor="middle" font-family="{MONO_STACK}" font-size="11" letter-spacing="4" fill="#4E4E58">{escape(note)}</text>')
    return svg_open(w, h, "\n".join(b))


def wrap_cn(text, max_px, f_cn=15, f_lat=8.4):
    """Greedy wrap that measures CJK as full-width."""
    lines, cur, acc = [], "", 0.0
    for ch in text:
        wch = f_cn if ord(ch) > 0x2E80 else f_lat
        if acc + wch > max_px:
            lines.append(cur)
            cur, acc = "", 0.0
        cur += ch
        acc += wch
    if cur:
        lines.append(cur)
    return lines


def card_svg(idx, total, title, desc, tags, w=800, h=214):
    b = []
    b.append(f'<rect width="{w}" height="{h}" fill="#08080A"/>')
    b.append(f'<rect x="0.75" y="0.75" width="{w-1.5}" height="{h-1.5}" fill="none" stroke="#23242B" stroke-width="1.5"/>')
    b.append(f'<rect x="0" y="0" width="4" height="{h}" fill="#B3121B"/>')
    b.append(f'<text x="38" y="44" font-family="{MONO_STACK}" font-size="12" letter-spacing="3.5" fill="#6C6C74">REEL {idx:02d} / {total:02d}</text>')
    b.append(f'<text x="{w-34}" y="44" text-anchor="end" font-family="{MONO_STACK}" font-size="11" letter-spacing="3" fill="#B3121B">PINNED</text>')
    b.append(f'<text x="38" y="96" font-family="{SERIF_STACK}" font-size="34" fill="#F2F0EB">{escape(title)}</text>')
    y = 130
    for line in wrap_cn(desc, w - 130):
        b.append(f'<text x="38" y="{y}" font-family="{SANS_CN}" font-size="15" fill="#9C9CA4">{escape(line)}</text>')
        y += 22
    b.append(f'<line x1="38" y1="{h-46}" x2="{w-38}" y2="{h-46}" stroke="#1C1C22" stroke-width="1"/>')
    b.append(f'<text x="38" y="{h-20}" font-family="{MONO_STACK}" font-size="12.5" letter-spacing="2.4" fill="#C3BDB2">{escape(tags)}</text>')
    b.append(f'<text x="{w-38}" y="{h-20}" text-anchor="end" font-family="{MONO_STACK}" font-size="12.5" letter-spacing="2.4" fill="#B3121B">OPEN →</text>')
    b.append(grain_rect(w, h, 0.05))
    return svg_open(w, h, "\n".join(b))


def footer_svg(w=1600, h=150):
    b = []
    b.append(f'<line x1="0" y1="1" x2="{w}" y2="1" stroke="#22232B" stroke-width="1"/>')
    b.append(f'<text x="{w//2}" y="58" text-anchor="middle" font-family="{MONO_STACK}" font-size="16" letter-spacing="9" fill="#6C6C74">END OF REEL</text>')
    b.append(f'<rect x="{w//2-120}" y="76" width="240" height="3" fill="#B3121B"/>')
    b.append(f'<text x="{w//2}" y="110" text-anchor="middle" font-family="{MONO_STACK}" font-size="12" letter-spacing="4" fill="#43434D">SHE NEVER LEFT  ·  35MM  ·  2026</text>')
    return svg_open(w, h, "\n".join(b))


def tech_rack_svg(w=1600, h=176):
    """Two rows of monospace chips — the noir answer to skill icons."""
    rows = [
        ["C", "C++", "PYTHON", "TYPESCRIPT", "JAVASCRIPT", "HTML / CSS", "RUST (LEARNING)"],
        ["OPENCV", "ROS2", "STM32 H7", "FREERTOS", "CAN / FDCAN", "ESP8266", "LINUX", "GIT"],
    ]
    b = []
    chip_h, gap_x, gap_y = 44, 14, 18
    y = 22
    for ri, row in enumerate(rows):
        widths = [max(88, int(len(t) * 9.6 + 40)) for t in row]
        total = sum(widths) + gap_x * (len(row) - 1)
        x = (w - total) // 2
        for ci, (label, cw) in enumerate(zip(row, widths)):
            accent = ri == 0 and ci == 1  # one lit chip, like a single red spotlight
            stroke = "#B3121B" if accent else "#26272F"
            fill = "#14100F" if accent else "#0B0B0E"
            text_c = "#F0EDE6" if accent else "#B9B9C2"
            b.append(
                f'<rect x="{x}" y="{y}" width="{cw}" height="{chip_h}" rx="2" fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>'
            )
            b.append(
                f'<text x="{x + cw//2}" y="{y + 29}" text-anchor="middle" font-family="{MONO_STACK}" '
                f'font-size="14" letter-spacing="2.2" fill="{text_c}">{escape(label)}</text>'
            )
            x += cw + gap_x
        y += chip_h + gap_y
    return svg_open(w, h, "\n".join(b))


CARDS = [
    (
        "LifeFlow-Web",
        "本地优先的今日时间线：不联网、不评判、只帮你重新开始。规划 / 专注 / 回顾全在浏览器里跑。",
        "TYPESCRIPT · REACT · VITE · PWA",
    ),
    (
        "Deepseek-Desktop-Mini-Maid",
        "把 DeepSeek 鲸鱼娘做进 1.54 寸圆屏：情绪联动表情、待机偷吃白饭、B 站语音点歌。",
        "PYTHON · LS26 / ARCS-MINI3 · 嵌入式",
    ),
    (
        "GEArm",
        "桌面六轴机械臂固件：从 STM32F407 全量移植到 DM-MC02（H723），bxCAN → FDCAN 重构。",
        "C · STM32H723 · FREERTOS · CANFD",
    ),
    (
        "Sc_vision · Ember",
        "26 赛季自瞄模块：IMM 单独建模旋转状态，压小陀螺；有限状态机火控，4m 内稳定跟打。",
        "C++ · OPENCV · 无 ROS 依赖",
    ),
    (
        "Desktop-companion",
        "桌面 Noir：本地模型与云端 API 双通道的桌面陪伴体，会记忆、会待机、会等你。",
        "JAVASCRIPT · 本地 LLM · DESKTOP",
    ),
    (
        "Multicar",
        "双芯小车平台：ESP8266 负责决策与 WiFi，STM32F103 负责执行，循迹与遥控。",
        "C · ESP8266 · STM32F103",
    ),
]


def main():
    made = []
    made.append(build_banner())
    made.append(build_strip())
    made.append(build_portrait(ASSETS / "character.png"))
    files = {
        "casefile.svg": casefile_svg(),
        "divider-act-i.svg": divider_svg("ACT I", "NOW IN PRODUCTION"),
        "divider-act-ii.svg": divider_svg("ACT II", "THE ARCHIVE"),
        "divider-act-iii.svg": divider_svg("ACT III", "HARDWARE & TELEMETRY"),
        "tech-rack.svg": tech_rack_svg(),
        "footer.svg": footer_svg(),
    }
    for i, (title, desc, tags) in enumerate(CARDS, 1):
        files[f"card-{i}.svg"] = card_svg(i, len(CARDS), title, desc, tags)
    for name, text in files.items():
        (ASSETS / name).write_text(text, encoding="utf-8")
    for path, size in made:
        print(f"{path.name:24s} {size[0]}x{size[1]}  {path.stat().st_size/1024:7.1f} KB")
    total = sum((ASSETS / n).stat().st_size for n in files) / 1024
    print(f"{len(files)} svg files, {total:.1f} KB")


if __name__ == "__main__":
    main()
