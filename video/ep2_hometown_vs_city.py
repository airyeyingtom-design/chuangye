import math
import os
import subprocess
import sys
import wave
from functools import lru_cache
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

from make_video import (ambience_noise, bandpass, lowpass, note, piano, place, reverb, sfx_click,
                        sfx_heart, sfx_tick, sfx_train, sfx_whoosh)

W, H, FPS, SR = 1920, 1080, 30, 44100
BAR = 118
FONT = "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"
OUT_DIR = os.path.dirname(os.path.abspath(__file__))
TMP = "/tmp/ep2_build"

HOME = (150, 220, 160)
CITY = (180, 165, 255)
INK = (14, 14, 20)


@lru_cache(None)
def font(size):
    return ImageFont.truetype(FONT, size)


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def smooth(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def lerp(a, b, t):
    return a + (b - a) * t


def lerpc(a, b, t):
    return tuple(int(lerp(a[i], b[i], t)) for i in range(3))


# ---------- drawing primitives ----------

def grad(w, h, stops):
    ys = np.linspace(0, 1, h)
    pos = [s[0] for s in stops]
    cols = np.array([s[1] for s in stops], dtype=float)
    arr = np.stack([np.interp(ys, pos, cols[:, c]) for c in range(3)], axis=1)
    arr = np.repeat(arr[:, None, :], w, axis=1).astype(np.uint8)
    return Image.fromarray(arr, "RGB").convert("RGBA")


class SD:
    """ImageDraw wrapper that scales coordinates, for drawing static layers at 2x."""

    def __init__(self, img, k):
        self.d = ImageDraw.Draw(img)
        self.k = k

    def _p(self, pts):
        return [(x * self.k, y * self.k) for x, y in pts]

    def rect(self, box, fill, r=0):
        b = [v * self.k for v in box]
        if r:
            self.d.rounded_rectangle(b, r * self.k, fill=fill)
        else:
            self.d.rectangle(b, fill=fill)

    def ellipse(self, box, fill):
        self.d.ellipse([v * self.k for v in box], fill=fill)

    def poly(self, pts, fill):
        self.d.polygon(self._p(pts), fill=fill)

    def line(self, pts, fill, w):
        self.d.line(self._p(pts), fill=fill, width=int(w * self.k))


def static_layer(w, h, painter, base=None, k=2):
    img = Image.new("RGBA", (w * k, h * k), (0, 0, 0, 0)) if base is None else base.resize((w * k, h * k))
    painter(SD(img, k))
    return img.resize((w, h), Image.LANCZOS)


@lru_cache(None)
def glow_sprite(r, color, power=2.0, strength=1.0):
    y, x = np.mgrid[-r:r, -r:r]
    d = np.sqrt(x * x + y * y) / r
    a = np.clip(1 - d, 0, 1) ** power * 255 * strength
    arr = np.zeros((2 * r, 2 * r, 4), np.uint8)
    arr[..., :3] = color
    arr[..., 3] = a.astype(np.uint8)
    return Image.fromarray(arr, "RGBA")


def put(canvas, sprite, x, y, alpha=1.0, anchor="center"):
    if alpha <= 0.003:
        return
    sw, sh = sprite.size
    if anchor == "center":
        x0, y0 = int(x - sw / 2), int(y - sh / 2)
    else:
        x0, y0 = int(x), int(y)
    cw, ch = canvas.size
    l, t, r, b = max(0, x0), max(0, y0), min(cw, x0 + sw), min(ch, y0 + sh)
    if l >= r or t >= b:
        return
    sp = sprite.crop((l - x0, t - y0, r - x0, b - y0))
    if alpha < 0.999:
        a = np.asarray(sp.getchannel("A"), dtype=np.float32) * alpha
        sp = sp.copy()
        sp.putalpha(Image.fromarray(a.astype(np.uint8)))
    canvas.alpha_composite(sp, (l, t))


def glow(canvas, x, y, r, color, alpha=1.0, power=2.0):
    put(canvas, glow_sprite(int(r), tuple(color), power), x, y, alpha)


# ---------- silhouettes ----------

@lru_cache(None)
def person(h, pose="stand", p=0.0, rim=(255, 200, 140), side=1, body=INK, face=1):
    """Silhouette sprite with rim light. Returns (sprite, feet_x, feet_y)."""
    k = 2
    S = h * k
    w, hh = int(h * 1.3) * k, int(h * 1.45) * k
    m = Image.new("L", (w, hh), 0)
    d = ImageDraw.Draw(m)
    ox, oy = w / 2, hh - 6 * k

    def P(x, y, s=1.0, bx=0.0, by=0.0):
        return (ox + (bx + x * s) * S, oy + (by + y * s) * S)

    def limb(a, b, wid):
        d.line([a, b], fill=255, width=max(1, int(wid * S)))
        r = wid * S / 2
        for c in (a, b):
            d.ellipse((c[0] - r, c[1] - r, c[0] + r, c[1] + r), fill=255)

    def vec(a, sd, ln, s):
        rad = math.radians(a)
        return (sd * math.sin(rad) * ln * s * S, math.cos(rad) * ln * s * S)

    def figure(s, bx, by, arms, legs, stoop=0.0, hair=None):
        sh_y, hip_y = -0.80, -0.47
        d.polygon([P(-0.045, sh_y - 0.015, s, bx, by), P(0.045, sh_y - 0.015, s, bx, by),
                   P(0.125, sh_y + 0.045, s, bx, by), P(0.08, hip_y, s, bx, by),
                   P(-0.08, hip_y, s, bx, by), P(-0.125, sh_y + 0.045, s, bx, by)], fill=255)
        for sd in (-1, 1):
            c = P(sd * 0.1, sh_y + 0.045, s, bx, by)
            r = 0.034 * s * S
            d.ellipse((c[0] - r, c[1] - r, c[0] + r, c[1] + r), fill=255)
        limb(P(stoop * 0.5, -0.81, s, bx, by), P(stoop, -0.86, s, bx, by), 0.05 * s)
        hc = P(stoop, -0.895, s, bx, by)
        hr = 0.068 * s * S
        d.ellipse((hc[0] - hr, hc[1] - hr * 1.1, hc[0] + hr, hc[1] + hr), fill=255)
        if hair == "long":
            d.polygon([P(stoop - 0.07, -0.9, s, bx, by), P(stoop + 0.07, -0.9, s, bx, by),
                       P(stoop + 0.085, -0.74, s, bx, by), P(stoop - 0.085, -0.74, s, bx, by)], fill=255)
        elif hair == "bun":
            c = P(stoop - face * 0.06, -0.93, s, bx, by)
            r = 0.035 * s * S
            d.ellipse((c[0] - r, c[1] - r, c[0] + r, c[1] + r), fill=255)
        hands = {}
        for sd, (a1, a2) in zip((-1, 1), arms):
            st = P(sd * 0.105, sh_y + 0.035, s, bx, by)
            v1 = vec(a1, sd, 0.17, s)
            el = (st[0] + v1[0], st[1] + v1[1])
            v2 = vec(a2, sd, 0.16, s)
            hd = (el[0] + v2[0], el[1] + v2[1])
            limb(st, el, 0.056 * s)
            limb(el, hd, 0.05 * s)
            hands[sd] = hd
        for sd, (l1, l2) in zip((-1, 1), legs):
            hp = P(sd * 0.05, hip_y, s, bx, by)
            v1 = vec(l1, sd, 0.25, s)
            kn = (hp[0] + v1[0], hp[1] + v1[1])
            v2 = vec(l2, sd, 0.25, s)
            ft = (kn[0] + v2[0], kn[1] + v2[1])
            limb(hp, kn, 0.078 * s)
            limb(kn, ft, 0.066 * s)
        return hands

    arms, legs, stoop, hair = [(8, 4), (8, 4)], [(3, 1), (3, 1)], 0.0, None
    if pose == "wave":
        arms = [(8, 4), (lerp(8, 150, p), lerp(4, 175, p))]
    elif pose == "toast":
        lift = (lerp(8, 75, p), lerp(4, 125, p))
        arms = [(8, 4), lift] if side == 1 else [lift, (8, 4)]
    elif pose == "run":
        ph = math.sin(p * 2 * math.pi)
        legs = [(28 * ph, 28 * ph - 25), (-28 * ph, -28 * ph - 25)]
        arms = [(-30 * ph, -30 * ph - 50), (30 * ph, 30 * ph - 50)]
    elif pose == "walk":
        ph = math.sin(p * 2 * math.pi)
        legs = [(14 * ph, 14 * ph - 6), (-14 * ph, -14 * ph - 6)]
        arms = [(-10 * ph + 6, -10 * ph), (10 * ph + 6, 10 * ph)]
    elif pose == "carry":
        arms = [(12, -70), (12, -70)]
        ph = math.sin(p * 2 * math.pi)
        legs = [(12 * ph, 12 * ph - 5), (-12 * ph, -12 * ph - 5)]
    elif pose == "kid":
        arms = [(160, 175), (160, 175)]
    elif pose == "elder":
        stoop, hair = 0.05 * face, "bun"
    elif pose == "elder_cane":
        stoop = 0.05 * face
        arms = [(8, 4), (22, 10)] if face == 1 else [(22, 10), (8, 4)]
    elif pose == "long":
        hair = "long"
        ph = math.sin(p * 2 * math.pi)
        legs = [(12 * ph, 12 * ph - 5), (-12 * ph, -12 * ph - 5)]
    elif pose == "head_down":
        stoop = 0.03
        arms = [(4, 2), (4, 2)]

    hands = figure(1.0, 0, 0, arms, legs, stoop, hair)
    if pose == "carry":
        d.rectangle((*P(-0.15, -0.66), *P(0.15, -0.46)), fill=255)
    if pose == "kid":
        figure(0.42, 0.0, -0.80, [(120, 160), (120, 160)], [(70, 10), (70, 10)])
    if pose == "elder_cane":
        hd = hands[1 if face == 1 else -1]
        d.line([hd, (hd[0] + face * 0.04 * S, oy)], fill=255, width=int(0.018 * S))
    if pose == "bride":
        d.polygon([P(-0.09, -0.5), P(0.09, -0.5), P(0.25, 0.02), P(-0.25, 0.02)], fill=255)
        d.polygon([P(0.02, -0.95), P(-0.10, -0.92), P(-0.22, -0.40), P(-0.08, -0.5)], fill=255)

    shifted = ImageChops.offset(m, -3 * k * side, 2 * k)
    rim_m = ImageChops.subtract(m, shifted).filter(ImageFilter.GaussianBlur(1.2 * k))
    rgb = Image.new("RGB", (w, hh), body)
    rgb.paste(Image.new("RGB", (w, hh), rim), (0, 0), rim_m)
    sp = rgb.convert("RGBA")
    sp.putalpha(m)
    sp = sp.resize((w // k, hh // k), Image.LANCZOS)
    return sp, w / 2 / k, oy / k


def put_person(canvas, fx, fy, h, pose="stand", p=0.0, rim=(255, 200, 140), side=1, alpha=1.0, face=1, body=INK):
    sp, ax, ay = person(int(h), pose, round(p, 2), tuple(rim), side, tuple(body), face)
    put(canvas, sp, fx - ax, fy - ay, alpha, anchor="topleft")


# ---------- text ----------

@lru_cache(None)
def text_sprite(s, size, color=(255, 255, 255), shadow=True):
    f = font(size)
    tmp = ImageDraw.Draw(Image.new("L", (1, 1)))
    l, t, r, b = tmp.textbbox((0, 0), s, font=f)
    pad = 30
    w, h = r - l + pad * 2, b - t + pad * 2
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    if shadow:
        sh = Image.new("L", (w, h), 0)
        ImageDraw.Draw(sh).text((pad - l + 2, pad - t + 3), s, font=f, fill=230)
        sh = sh.filter(ImageFilter.GaussianBlur(size / 7))
        img = Image.merge("RGBA", (*[Image.new("L", (w, h), 0)] * 3, sh))
    ImageDraw.Draw(img).text((pad - l, pad - t), s, font=f, fill=tuple(color) + (255,))
    return img


def draw_text(canvas, s, x, y, size, color=(255, 255, 255), alpha=1.0, blur=0.0, scale=1.0):
    sp = text_sprite(s, size, tuple(color))
    if scale != 1.0:
        sp = sp.resize((max(1, int(sp.width * scale)), max(1, int(sp.height * scale))), Image.BILINEAR)
    if blur > 0.3:
        sp = sp.filter(ImageFilter.GaussianBlur(blur))
    put(canvas, sp, x, y, alpha)


def fade_window(lt, t0, t1, fin=0.5, fout=0.5):
    return min(ease((lt - t0) / fin), ease((t1 - lt) / fout))


# ---------- particles ----------

def rain(ov, w, h, t, n=160, seed=1, region=None, color=(200, 210, 235), alpha=70, slant=0.18, length=38):
    rng = np.random.default_rng(seed)
    x0, y0, x1, y1 = region or (0, 0, w, h)
    d = ImageDraw.Draw(ov)
    xs = rng.uniform(x0, x1, n)
    ys = rng.uniform(0, 1, n)
    sp = rng.uniform(900, 1500, n)
    for x, y, s in zip(xs, ys, sp):
        yy = y0 + ((y * (y1 - y0) + s * t) % (y1 - y0))
        xx = x + slant * (yy - y0)
        xx = x0 + (xx - x0) % (x1 - x0)
        d.line((xx, yy, xx + slant * length, yy + length), fill=color + (alpha,), width=2)


def snow(ov, w, h, t, n=120, seed=2, region=None):
    rng = np.random.default_rng(seed)
    x0, y0, x1, y1 = region or (0, 0, w, h)
    d = ImageDraw.Draw(ov)
    for i in range(n):
        bx, by = rng.uniform(x0, x1), rng.uniform(0, 1)
        sp, ph, r = rng.uniform(40, 110), rng.uniform(0, 6.28), rng.uniform(1.5, 4)
        yy = y0 + ((by * (y1 - y0) + sp * t) % (y1 - y0))
        xx = bx + math.sin(t * 0.8 + ph) * 18
        d.ellipse((xx - r, yy - r, xx + r, yy + r), fill=(255, 255, 255, 200))


def motes(ov, w, h, t, n=50, seed=3, color=(255, 230, 190), region=None):
    rng = np.random.default_rng(seed)
    x0, y0, x1, y1 = region or (0, 0, w, h)
    d = ImageDraw.Draw(ov)
    for i in range(n):
        bx, by = rng.uniform(x0, x1), rng.uniform(y0, y1)
        ph, r = rng.uniform(0, 6.28), rng.uniform(1, 2.6)
        xx = bx + math.sin(t * 0.3 + ph) * 30
        yy = by + math.cos(t * 0.25 + ph) * 20 - t * 6
        yy = y0 + (yy - y0) % (y1 - y0)
        a = int(90 + 80 * math.sin(t * 1.3 + ph))
        d.ellipse((xx - r, yy - r, xx + r, yy + r), fill=color + (max(0, a),))


def burst(ov, cx, cy, age, color, n=48, speed=260, seed=0, life=1.8, size=3.0, gravity=120):
    if age < 0 or age > life:
        return
    rng = np.random.default_rng(seed)
    d = ImageDraw.Draw(ov)
    fade = (1 - age / life) ** 1.5
    for i in range(n):
        ang = i / n * 2 * math.pi + rng.uniform(-0.05, 0.05)
        v = speed * rng.uniform(0.75, 1.0)
        dist = v * (1 - math.exp(-age * 2.2)) / 2.2
        x = cx + math.cos(ang) * dist
        y = cy + math.sin(ang) * dist + gravity * age * age
        r = size * (0.6 + fade)
        tx = cx + math.cos(ang) * dist * 0.72
        ty = cy + math.sin(ang) * dist * 0.72 + gravity * age * age * 0.8
        d.line((tx, ty, x, y), fill=tuple(color) + (int(120 * fade),), width=max(1, int(r * 0.8)))
        d.ellipse((x - r, y - r, x + r, y + r), fill=tuple(color) + (int(255 * fade),))


def sparks(ov, cx, cy, t, seed, spread=60, rate=26):
    rng = np.random.default_rng(seed)
    d = ImageDraw.Draw(ov)
    for i in range(int(rate * 1.2)):
        t0 = (i / rate + rng.uniform(0, 0.03))
        age = (t - t0) % 1.2
        ang = rng.uniform(-math.pi, 0)
        v = rng.uniform(120, 320)
        x = cx + rng.uniform(-spread, spread) + math.cos(ang) * v * age
        y = cy + math.sin(ang) * v * age + 400 * age * age
        a = int(255 * max(0, 1 - age / 0.7))
        if a > 0:
            d.ellipse((x - 2.5, y - 2.5, x + 2.5, y + 2.5), fill=(255, 210, 120, a))


# ---------- scenes ----------

def camera(img, lt, dur, zoom=0.045, pan=(0.0, 0.0)):
    w, h = img.size
    s = 1 + zoom * smooth(lt / dur)
    cw, ch = w / s, h / s
    cx = w / 2 + pan[0] * w * smooth(lt / dur)
    cy = h / 2 + pan[1] * h * smooth(lt / dur)
    box = (cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2)
    return img.transform((w, h), Image.EXTENT, box, Image.BILINEAR)


# station ------------------------------------------------------------

@lru_cache(None)
def station_layers(dawn):
    if dawn:
        stops = [(0, (70, 92, 140)), (0.45, (178, 160, 190)), (0.66, (250, 205, 175)), (0.72, (255, 228, 195)), (1, (255, 228, 195))]
        town, rim_c = (120, 108, 138), (255, 220, 190)
    else:
        stops = [(0, (24, 20, 52)), (0.42, (110, 52, 86)), (0.64, (235, 120, 74)), (0.72, (255, 182, 110)), (1, (255, 182, 110))]
        town, rim_c = (66, 36, 56), (255, 190, 120)
    sky = grad(W, H, stops)
    glow(sky, 1360, 760, 620, (255, 170, 100) if not dawn else (255, 230, 200), 0.7)

    def paint(s):
        rng = np.random.default_rng(5)
        x = 0
        while x < W:
            bw, bh = rng.integers(40, 120), rng.integers(20, 70)
            s.rect((x, 770 - bh, x + bw, 772), town)
            if rng.random() < 0.3:
                s.poly([(x - 4, 770 - bh), (x + bw / 2, 770 - bh - 24), (x + bw + 4, 770 - bh)], town)
            x += bw + rng.integers(0, 30)
        for px in range(150, W, 420):
            s.rect((px, 520, px + 8, 790), (36, 26, 36))
            s.rect((px - 40, 530, px + 48, 538), (36, 26, 36))
        s.line([(0, 545), (W, 548)], (36, 26, 36), 2)
        s.line([(0, 566), (W, 570)], (36, 26, 36), 2)
        s.rect((0, 772, W, 870), (34, 26, 32))
        s.line([(0, 830), (W, 830)], (140, 110, 110), 3)
        s.line([(0, 858), (W, 858)], (140, 110, 110), 4)
    bg = static_layer(W, H, paint, base=sky)

    def paint_fg(s):
        s.poly([(0, 872), (W, 872), (W, H), (0, H)], (40, 34, 42))
        s.rect((0, 868, W, 882), (210, 178, 70))
        for lx in (230, 1720):
            s.rect((lx, 380, lx + 18, 1000), (22, 20, 26))
            s.rect((lx - 30, 370, lx + 48, 392), (22, 20, 26), r=6)
        s.rect((1380, 930, 1620, 948), (24, 22, 28))
        s.rect((1395, 948, 1405, 1000), (24, 22, 28))
        s.rect((1595, 948, 1605, 1000), (24, 22, 28))
    fg = static_layer(W, H, paint_fg)
    for lx in (239, 1729):
        glow(fg, lx, 400, 120, (255, 220, 160), 0.8)
    return bg, fg, rim_c


def draw_train(c, x0, passenger=True, alpha=1.0, rim=(255, 200, 140)):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    L = 3400
    d.rounded_rectangle((x0, 600, x0 + L, 842), 30, fill=(26, 28, 38, 255))
    d.rectangle((x0, 598, x0 + L, 612), fill=(60, 64, 80, 255))
    wins = [(x0 + 60 + i * 130, 652, x0 + 160 + i * 130, 722) for i in range(int((L - 120) / 130))]
    for wx0, wy0, wx1, wy1 in wins:
        d.rounded_rectangle((wx0, wy0, wx1, wy1), 8, fill=(255, 216, 160, 255))
    d.rectangle((x0, 760, x0 + L, 772), fill=(200, 60, 50, 255))
    if passenger:
        wx0, wy0, wx1, wy1 = wins[15]
        sp, ax, ay = person(250, "wave", 0.6, rim, 1)
        tmp = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        put(tmp, sp, (wx0 + wx1) / 2 - ax, 850 - ay, 1.0, anchor="topleft")
        mask = Image.new("L", (W, H), 0)
        ImageDraw.Draw(mask).rounded_rectangle((wx0, wy0, wx1, wy1), 8, fill=255)
        layer.paste(tmp, (0, 0), ImageChops.multiply(mask, tmp.getchannel("A")))
    for wx0, wy0, wx1, wy1 in wins:
        glow(layer, (wx0 + wx1) / 2, 690, 90, (255, 200, 140), 0.25)
    if alpha < 1:
        a = np.asarray(layer.getchannel("A"), np.float32) * alpha
        layer.putalpha(Image.fromarray(a.astype(np.uint8)))
    c.alpha_composite(layer)


def scene_station(lt, dur, dawn=False):
    bg, fg, rim = station_layers(dawn)
    c = bg.copy()
    if not dawn:
        t = max(0.0, lt - 1.0)
        tx = -900 - 0.5 * 240 * t * t
        draw_train(c, tx + 0, True, 1.0, rim=CITY)
        c.alpha_composite(fg)
        wave = ease((lt - 2.2) / 0.7)
        put_person(c, 760, 1012, 360, "wave", wave, rim=HOME, side=1)
    else:
        tx = 2200 - 1400 * max(0.0, lt - 2.0)
        if tx > -3500:
            draw_train(c, tx, False, 0.85)
        c.alpha_composite(fg)
        put_person(c, 860, 1012, 350, "stand", 0, rim=HOME, side=-1)
        put_person(c, 1050, 1012, 356, "stand", 0, rim=CITY, side=1)
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    motes(ov, W, H, lt, 60, 3, (255, 220, 180), (900, 300, 1900, 900))
    c.alpha_composite(ov)
    return camera(c, lt, dur, 0.05)


# home kitchen / city office (23) -----------------------------------

HW = W // 2


@lru_cache(None)
def kitchen_layers():
    bg = grad(HW, H, [(0, (70, 46, 34)), (1, (40, 26, 20))])

    def paint(s):
        s.rect((520, 250, 880, 560), (40, 58, 104))
        rng = np.random.default_rng(1)
        for _ in range(14):
            x, y = rng.uniform(530, 870), rng.uniform(430, 550)
            s.rect((x, y, x + 6, y + 8), (255, 210, 130))
        s.poly([(520, 480), (600, 440), (700, 470), (800, 430), (880, 460), (880, 560), (520, 560)], (24, 34, 60))
        s.rect((510, 240, 890, 256), (110, 80, 56))
        s.rect((510, 554, 890, 572), (110, 80, 56))
        s.rect((694, 250, 706, 560), (110, 80, 56))
        s.line([(380, 118), (380, 240)], (30, 20, 16), 3)
        s.poly([(330, 240), (430, 240), (410, 210), (350, 210)], (200, 150, 80))
    bg = static_layer(HW, H, paint, base=bg)
    glow(bg, 380, 300, 520, (255, 200, 130), 0.55, 1.6)

    def paint_fg(s):
        s.rect((60, 780, 900, 800), (140, 96, 60))
        s.rect((60, 800, 900, H), (70, 46, 30))
        for bx, col in ((260, (230, 230, 220)), (420, (200, 80, 60)), (580, (230, 230, 220)), (720, (120, 170, 90))):
            s.ellipse((bx - 60, 760, bx + 60, 792), col)
            s.ellipse((bx - 50, 764, bx + 50, 784), tuple(int(v * 0.7) for v in col))
    fg = static_layer(HW, H, paint_fg)
    return bg, fg


def half_kitchen(lt, dur):
    bg, fg = kitchen_layers()
    c = bg.copy()
    put_person(c, 300, 930, 430, "stand", 0, rim=(255, 196, 130), side=1)
    put_person(c, 700, 930, 400, "elder", 0, rim=(255, 196, 130), side=-1, face=-1)
    c.alpha_composite(fg)
    ov = Image.new("RGBA", (HW, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    rng = np.random.default_rng(9)
    for bx in (260, 420, 580):
        for i in range(10):
            ph = rng.uniform(0, 1)
            age = (lt * 0.35 + ph) % 1.0
            x = bx + math.sin(age * 9 + i) * 22
            y = 770 - age * 260
            r = 14 + age * 30
            a = int(70 * (1 - age))
            d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255, a))
    ov = ov.filter(ImageFilter.GaussianBlur(8))
    c.alpha_composite(ov)
    return camera(c, lt, dur, 0.05)


@lru_cache(None)
def office_layers():
    bg = grad(HW, H, [(0, (10, 14, 26)), (1, (6, 8, 14))])

    def paint(s):
        s.rect((40, 160, 920, 700), (20, 30, 56))
        rng = np.random.default_rng(4)
        x = 40
        while x < 920:
            bw, bh = rng.integers(40, 90), rng.integers(150, 480)
            s.rect((x, 700 - bh, x + bw, 700), (12, 18, 36))
            for wy in range(int(700 - bh + 10), 690, 18):
                for wx in range(int(x + 6), int(x + bw - 8), 14):
                    if rng.random() < 0.3:
                        s.rect((wx, wy, wx + 6, wy + 8), (255, 220, 150) if rng.random() < 0.7 else (150, 200, 255))
            x += bw + rng.integers(2, 10)
        for fx in (40, 480, 920):
            s.rect((fx - 6, 160, fx + 6, 700), (8, 10, 18))
    bg = static_layer(HW, H, paint, base=bg)
    rng = np.random.default_rng(8)
    for _ in range(14):
        glow(bg, rng.uniform(60, 900), rng.uniform(300, 680), rng.uniform(20, 50),
             (255, 200, 140) if rng.random() < 0.6 else (130, 180, 255), 0.35, 1.0)

    def paint_fg(s):
        s.rect((0, 790, HW, 808), (40, 44, 58))
        s.rect((0, 808, HW, H), (16, 18, 26))
        s.rect((500, 560, 800, 760), (20, 22, 30), r=8)
        s.rect((512, 572, 788, 748), (90, 150, 230))
        s.rect((630, 760, 670, 790), (20, 22, 30))
        for i in range(6):
            s.rect((530, 600 + i * 22, 530 + (i * 47 % 200) + 40, 610 + i * 22), (200, 230, 255))
    fg = static_layer(HW, H, paint_fg)
    glow(fg, 600, 660, 380, (110, 170, 255), 0.45, 1.6)
    return bg, fg


def half_office(lt, dur):
    bg, fg = office_layers()
    c = bg.copy()
    ov = Image.new("RGBA", (HW, H), (0, 0, 0, 0))
    rain(ov, HW, H, lt, 140, 11, (40, 160, 920, 700), alpha=60)
    c.alpha_composite(ov)
    put_person(c, 330, 960, 440, "head_down", 0, rim=(130, 180, 255), side=1)
    c.alpha_composite(fg)
    blink = 1 if int(lt * 2) % 2 == 0 else 0.4
    draw_text(c, "01:07", 820, 220, 34, (255, 90, 80), 0.9 * blink)
    return camera(c, lt, dur, 0.05)


# wedding / leaving (27) -----------------------------------------------

@lru_cache(None)
def wedding_layers():
    bg = grad(HW, H, [(0, (14, 14, 34)), (0.7, (40, 22, 40)), (1, (30, 16, 24))])

    def paint(s):
        rng = np.random.default_rng(3)
        for hx in (0, 300, 620):
            s.rect((hx, 430, hx + 300, 760), (30, 22, 30))
            s.poly([(hx - 20, 430), (hx + 150, 340), (hx + 320, 430)], (24, 16, 22))
            for wx in (hx + 60, hx + 200):
                s.rect((wx, 520, wx + 50, 590), (255, 190, 110))
        s.rect((0, 760, HW, H), (46, 30, 30))
        for tx in (150, 480, 810):
            s.ellipse((tx - 120, 780, tx + 120, 830), (170, 40, 40))
            for g in range(5):
                gx = tx - 100 + g * 50
                s.ellipse((gx - 14, 728, gx + 14, 756), (22, 16, 20))
                s.rect((gx - 16, 752, gx + 16, 800), (22, 16, 20), r=8)
    return static_layer(HW, H, paint, base=bg)


def half_wedding(lt, dur):
    c = wedding_layers().copy()
    d = ImageDraw.Draw(c)
    for row, y in enumerate((210, 300)):
        pts = []
        for i in range(9):
            x = i * 120 + (60 if row else 0)
            sway = math.sin(lt * 1.6 + i + row) * 5
            yy = y + 30 * math.sin(i / 8 * math.pi) + sway
            pts.append((x, yy))
        d.line(pts, fill=(60, 30, 30, 255), width=2)
        for x, yy in pts:
            d.ellipse((x - 16, yy, x + 16, yy + 38), fill=(220, 40, 40, 255))
            d.rectangle((x - 6, yy + 38, x + 6, yy + 46), fill=(250, 200, 80, 255))
            glow(c, x, yy + 20, 60, (255, 80, 60), 0.35)
    glow(c, 480, 820, 360, (255, 120, 80), 0.25)
    put_person(c, 420, 1000, 400, "stand", 0, rim=(255, 140, 110), side=-1)
    put_person(c, 560, 1000, 370, "bride", 0, rim=(255, 210, 200), side=1, body=(40, 30, 36))
    ov = Image.new("RGBA", (HW, H), (0, 0, 0, 0))
    sparks(ov, 130, 960, lt, 21)
    sparks(ov, 830, 960, lt + 0.4, 22)
    c.alpha_composite(ov)
    glow(c, 130, 940, 160, (255, 200, 120), 0.3 + 0.2 * math.sin(lt * 30))
    glow(c, 830, 940, 160, (255, 200, 120), 0.3 + 0.2 * math.sin(lt * 27))
    return camera(c, lt, dur, 0.05)


@lru_cache(None)
def rental_layers():
    bg = grad(HW, H, [(0, (30, 34, 46)), (1, (18, 20, 28))])

    def paint(s):
        s.rect((120, 250, 420, 560), (24, 34, 64))
        rng = np.random.default_rng(6)
        x = 120
        while x < 420:
            bw, bh = rng.integers(30, 60), rng.integers(80, 250)
            s.rect((x, 560 - bh, x + bw, 560), (14, 20, 40))
            x += bw + 4
        s.rect((112, 242, 428, 256), (60, 64, 76))
        s.rect((112, 554, 428, 568), (60, 64, 76))
        s.rect((0, 800, HW, H), (36, 38, 48))
        s.rect((690, 300, 860, 800), (10, 10, 14))
        for bx, by, bw2, bh2 in ((470, 690, 140, 110), (500, 600, 110, 90), (90, 720, 120, 80)):
            s.rect((bx, by, bx + bw2, by + bh2), (120, 92, 66))
            s.rect((bx, by + bh2 * 0.4, bx + bw2, by + bh2 * 0.5), (150, 120, 90))
    return static_layer(HW, H, paint, base=bg)


def half_rental(lt, dur):
    c = rental_layers().copy()
    close = smooth((lt - 7.0) / 0.9)
    door_w = 170 * (1 - close)
    if door_w > 2:
        d = ImageDraw.Draw(c)
        d.rectangle((690, 300, 690 + door_w, 800), fill=(255, 210, 150, 255))
        glow(c, 690 + door_w / 2, 600, 260 * (1 - close) + 20, (255, 200, 140), 0.5)
    walk = smooth((lt - 1.5) / 5.0)
    gx = lerp(560, 770, walk)
    galpha = 1 - smooth((lt - 6.3) / 0.6)
    put_person(c, gx, 900, 400, "long", (lt * 0.9) % 1, rim=(255, 200, 150), side=1, alpha=galpha)
    put_person(c, 280, 960, 380, "head_down", 0, rim=(150, 160, 210), side=1)
    d = ImageDraw.Draw(c)
    d.rectangle((140, 860, 460, 1000), fill=(50, 52, 66, 255))
    d.rectangle((140, 850, 460, 872), fill=(80, 84, 100, 255))
    return camera(c, lt, dur, 0.05)


# riverside / balcony (31) ---------------------------------------------

@lru_cache(None)
def river_layers():
    bg = grad(HW, H, [(0, (60, 50, 110)), (0.45, (240, 140, 110)), (0.58, (255, 200, 140)), (1, (255, 200, 140))])
    glow(bg, 560, 600, 300, (255, 220, 160), 0.8)

    def paint(s):
        rng = np.random.default_rng(2)
        for i in range(22):
            tx = i * 46 + rng.uniform(-10, 10)
            r = rng.uniform(28, 46)
            s.ellipse((tx - r, 600 - r * 1.6, tx + r, 620), (60, 40, 50))
        s.rect((0, 610, HW, 760), (210, 130, 110))
        s.rect((0, 760, HW, H), (40, 34, 30))
        s.poly([(0, 760), (HW, 740), (HW, 780), (0, 790)], (60, 50, 40))
    return static_layer(HW, H, paint, base=bg)


def half_river(lt, dur):
    c = river_layers().copy()
    d = ImageDraw.Draw(c)
    for i in range(26):
        y = 620 + i * 5.5
        off = math.sin(lt * 1.5 + i) * 40
        xc = 560 + off
        wl = 80 - i * 2
        d.line((xc - wl, y, xc + wl, y), fill=(255, 230, 180, 140), width=2)
    walk = lt * 8
    put_person(c, 330 + walk, 960, 400, "kid", 0, rim=(255, 210, 160), side=1)
    put_person(c, 530 + walk, 960, 360, "elder_cane", 0, rim=(255, 210, 160), side=1, face=-1)
    ov = Image.new("RGBA", (HW, H), (0, 0, 0, 0))
    motes(ov, HW, H, lt, 40, 5, (255, 240, 200), (0, 400, HW, 900))
    c.alpha_composite(ov)
    return camera(c, lt, dur, 0.04, (0.02, 0))


@lru_cache(None)
def balcony_layers():
    bg = grad(HW, H, [(0, (40, 30, 80)), (0.55, (150, 90, 130)), (1, (60, 40, 70))])

    def paint(s):
        rng = np.random.default_rng(12)
        x = 0
        while x < HW:
            bw, bh = rng.integers(30, 80), rng.integers(100, 360)
            s.rect((x, 860 - bh, x + bw, 860), (34, 26, 54))
            for wy in range(int(860 - bh + 8), 850, 14):
                for wx in range(int(x + 4), int(x + bw - 6), 10):
                    if rng.random() < 0.35:
                        s.rect((wx, wy, wx + 4, wy + 6), (255, 210, 140))
            x += bw + rng.integers(0, 8)
        s.rect((0, 860, HW, H), (26, 22, 34))
        s.rect((0, 760, HW, 776), (20, 18, 26))
        for px in range(10, HW, 46):
            s.rect((px, 776, px + 6, 880), (20, 18, 26))
        s.line([(560, 200), (920, 230)], (20, 18, 26), 2)
        for sx in (620, 720, 820):
            s.poly([(sx, 205 + (sx - 560) * 0.08), (sx + 50, 210 + (sx - 560) * 0.08), (sx + 44, 280), (sx + 6, 280)], (30, 26, 40))
    return static_layer(HW, H, paint, base=bg)


def half_balcony(lt, dur):
    c = balcony_layers().copy()
    put_person(c, 300, 900, 380, "elder", 0, rim=(255, 180, 200), side=-1, face=-1)
    d = ImageDraw.Draw(c)
    d.rectangle((0, 760, HW, 776), fill=(20, 18, 26, 255))
    for px in range(10, HW, 46):
        d.rectangle((px, 776, px + 6, 880), fill=(20, 18, 26, 255))
    d.rectangle((0, 870, HW, H), fill=(26, 22, 34, 255))
    return camera(c, lt, dur, 0.05, (-0.02, 0))


# the call (35) ------------------------------------------------------

def phones(lt):
    c = Image.new("RGBA", (W, H), (4, 4, 8, 255))
    for i, (x, col, label) in enumerate(((640, HOME, "老家"), (1280, CITY, "城市"))):
        buzz = (int(lt * 3) % 2 == 0) and lt < 3.2
        jx = math.sin(lt * 120 + i) * 5 if buzz else 0
        glow(c, x, 540, 360, (120, 140, 200), 0.18)
        d = ImageDraw.Draw(c)
        d.rounded_rectangle((x - 130 + jx, 290, x + 130 + jx, 790), 36, fill=(20, 20, 26, 255))
        d.rounded_rectangle((x - 118 + jx, 304, x + 118 + jx, 776), 28, fill=(28, 34, 52, 255))
        draw_text(c, "03:12", x + jx, 370, 60, (230, 232, 240))
        draw_text(c, "妈妈", x + jx, 500, 54, (255, 255, 255))
        draw_text(c, "来电", x + jx, 560, 30, (180, 186, 210))
        d.ellipse((x - 90 + jx, 660, x - 30 + jx, 720), fill=(220, 70, 70, 255))
        d.ellipse((x + 30 + jx, 660, x + 90 + jx, 720), fill=(70, 200, 110, 255))
        draw_text(c, label, x, 250, 32, col, 0.9)
    return c


@lru_cache(None)
def corridor_bg():
    c = grad(HW, H, [(0, (150, 170, 170)), (1, (90, 110, 110))])

    def paint(s):
        vx, vy = 480, 520
        s.poly([(0, H), (HW, H), (vx + 60, vy + 40), (vx - 60, vy + 40)], (120, 140, 140))
        s.poly([(0, 0), (HW, 0), (vx + 60, vy - 40), (vx - 60, vy - 40)], (190, 205, 205))
        s.poly([(0, 0), (vx - 60, vy - 40), (vx - 60, vy + 40), (0, H)], (150, 170, 168))
        s.poly([(HW, 0), (vx + 60, vy - 40), (vx + 60, vy + 40), (HW, H)], (140, 160, 158))
        s.rect((vx - 60, vy - 40, vx + 60, vy + 40), (230, 240, 240))
    return static_layer(HW, H, paint, base=c)


def half_corridor(lt, dur):
    c = corridor_bg().copy()
    d = ImageDraw.Draw(c)
    vx, vy = 480, 520
    for i in range(8):
        z = ((i / 8) + lt * 0.9) % 1.0
        s = 0.08 + z ** 2.2 * 1.6
        y = vy - 40 - (vy - 40 - 0) * z ** 2.2 * 0.95
        hw = 60 + (HW / 2) * z ** 2.2 * 0.8
        d.rectangle((vx - hw * 0.5, y - 6 * s, vx + hw * 0.5, y + 6 * s), fill=(255, 255, 250, 255))
    put_person(c, 480, 880 - 6 * abs(math.sin(lt * 9)), 300, "run", (lt * 2.2) % 1, rim=(240, 255, 250), side=1)
    ov = Image.new("RGBA", (HW, H), (60, 255, 200, 18))
    c.alpha_composite(ov)
    return camera(c, lt, dur, 0.08)


def half_highway(lt, dur, clock_text):
    c = grad(HW, H, [(0, (6, 8, 16)), (0.5, (12, 14, 26)), (1, (4, 4, 8))])
    d = ImageDraw.Draw(c)
    vx, vy = 480, 520
    d.polygon([(vx - 10, vy), (vx + 10, vy), (HW + 200, 900), (-200, 900)], fill=(18, 18, 24, 255))
    for i in range(10):
        z = ((i / 10) + lt * 1.6) % 1.0
        zz = z ** 2.0
        y0, y1 = vy + (900 - vy) * zz, vy + (900 - vy) * min(1, (z + 0.04) ** 2.0)
        w0, w1 = 2 + 14 * zz, 2 + 14 * min(1, (z + 0.04) ** 2)
        d.polygon([(vx - w0, y0), (vx + w0, y0), (vx + w1, y1), (vx - w1, y1)], fill=(220, 220, 200, 255))
    rng = np.random.default_rng(31)
    for i in range(6):
        bx = vx + rng.uniform(-200, 200) + math.sin(lt * 0.6 + i) * 10
        by = vy + rng.uniform(10, 120)
        glow(c, bx, by, rng.uniform(20, 46), (255, 40, 40), 0.75)
    ov = Image.new("RGBA", (HW, H), (0, 0, 0, 0))
    rain(ov, HW, H, lt, 120, 41, (0, 120, HW, 900), color=(180, 190, 220), alpha=80, slant=0.05, length=24)
    od = ImageDraw.Draw(ov)
    rng = np.random.default_rng(42)
    for i in range(70):
        x, y, r = rng.uniform(0, HW), rng.uniform(140, 860), rng.uniform(3, 9)
        od.ellipse((x - r, y - r, x + r, y + r), fill=(200, 210, 240, 70))
    c.alpha_composite(ov)
    d = ImageDraw.Draw(c)
    d.rectangle((0, 860, HW, H), fill=(8, 8, 12, 255))
    d.arc((180, 760, 780, 1300), 200, 340, fill=(20, 20, 26, 255), width=46)
    for hx in (300, 660):
        d.ellipse((hx - 34, 790, hx + 34, 850), fill=(22, 22, 28, 255))
    glow(c, 840, 190, 90, (90, 200, 255), 0.35)
    draw_text(c, clock_text, 840, 190, 44, (120, 220, 255))
    return camera(c, lt, dur, 0.03)


@lru_cache(None)
def or_bg():
    c = grad(W, H, [(0, (40, 48, 60)), (1, (20, 24, 32))])

    def paint(s):
        s.rect((0, 860, W, H), (30, 34, 44))
        s.rect((660, 280, 1260, 860), (70, 80, 92))
        s.rect((676, 296, 954, 860), (110, 122, 134))
        s.rect((966, 296, 1244, 860), (110, 122, 134))
        s.rect((760, 400, 870, 520), (40, 50, 64))
        s.rect((1050, 400, 1160, 520), (40, 50, 64))
        s.rect((800, 170, 1120, 250), (40, 10, 14), r=10)
    return static_layer(W, H, paint, base=c)


def scene_or(lt, dur):
    c = or_bg().copy()
    pulse = 0.7 + 0.3 * math.sin(lt * 2.4)
    glow(c, 960, 210, 520, (255, 40, 40), 0.35 * pulse)
    draw_text(c, "手 术 中", 960, 208, 54, (255, 70, 70), 1.0, scale=1.0)
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(ov).polygon([(680, 862), (1240, 862), (1500, H), (420, H)], fill=(255, 60, 60, int(30 * pulse)))
    c.alpha_composite(ov)
    put_person(c, 960, 1000, 470, "head_down", 0, rim=(255, 90, 90), side=1)
    return camera(c, lt, dur, 0.07)


# 39: county office / layoff street ---------------------------------

@lru_cache(None)
def county_office_layers():
    bg = grad(HW, H, [(0, (120, 118, 104)), (1, (80, 76, 66))])

    def paint(s):
        s.rect((520, 220, 880, 560), (190, 200, 196))
        s.rect((690, 220, 702, 560), (90, 86, 74))
        s.rect((510, 214, 890, 228), (90, 86, 74))
        s.rect((510, 556, 890, 570), (90, 86, 74))
        s.rect((120, 250, 330, 470), (232, 228, 214))
        s.rect((120, 250, 330, 300), (190, 60, 50))
        s.rect((0, 790, HW, 806), (110, 90, 66))
        s.rect((0, 806, HW, H), (66, 54, 42))
        s.rect((480, 690, 640, 790), (40, 40, 44), r=6)
        s.rect((490, 700, 630, 780), (140, 160, 150))
        for i in range(4):
            s.rect((700, 760 - i * 14, 860, 772 - i * 14), (230, 226, 210))
    return static_layer(HW, H, paint, base=bg)


def half_county(lt, dur):
    c = county_office_layers().copy()
    put_person(c, 300, 960, 430, "stand", 0, rim=(255, 240, 210), side=1)
    d = ImageDraw.Draw(c)
    d.rectangle((0, 790, HW, 806), fill=(110, 90, 66, 255))
    d.rectangle((0, 806, HW, H), fill=(66, 54, 42, 255))
    d.rounded_rectangle((480, 690, 640, 790), 6, fill=(40, 40, 44, 255))
    d.rectangle((490, 700, 630, 780), fill=(140, 160, 150, 255))
    years = int(clamp(lt / 7.0) * 10)
    flip = (lt * 8) % 1
    month = int(lt * 8) % 12 + 1
    d.rectangle((120, 300, 330, 470), fill=(232, 228, 214, 255))
    if lt < 7.2:
        d.polygon([(120, 300), (330, 300), (330, 300 + 170 * (1 - flip)), (120, 300 + 170 * (1 - flip))], fill=(245, 242, 230, 255))
    draw_text(c, f"{2023 + years}", 225, 276, 30, (255, 240, 230))
    draw_text(c, f"{month if lt < 7.2 else 12}", 225, 390, 80, (60, 50, 44), 1.0)
    ov = Image.new("RGBA", (HW, H), (0, 0, 0, 0))
    ImageDraw.Draw(ov).polygon([(520, 220), (880, 220), (560, 1080), (100, 1080)], fill=(255, 250, 230, 22))
    motes(ov, HW, H, lt, 50, 8, (255, 250, 230), (150, 300, 800, 1000))
    c.alpha_composite(ov)
    return camera(c, lt, dur, 0.04)


@lru_cache(None)
def street_layers():
    bg = grad(HW, H, [(0, (60, 70, 110)), (0.6, (150, 120, 140)), (1, (60, 60, 80))])

    def paint(s):
        s.rect((80, 120, 880, 820), (30, 40, 64))
        for gx in range(80, 880, 50):
            for gy in range(130, 820, 40):
                lit = (gx * 7 + gy * 3) % 11 < 4
                s.rect((gx + 4, gy + 4, gx + 46, gy + 36), (140, 158, 190) if lit else (36, 46, 70))
        s.rect((0, 820, HW, H), (40, 40, 50))
        s.rect((0, 820, HW, 830), (90, 90, 100))
    return static_layer(HW, H, paint, base=bg)


def half_street(lt, dur):
    c = street_layers().copy()
    for i in range(5):
        x = (HW + 200) - ((lt * 260 + i * 260) % (HW + 400))
        put_person(c, x, 980, 360, "walk", (lt * 1.4 + i * 0.3) % 1, rim=(160, 170, 210), side=1, alpha=0.55)
    bx = lerp(760, 380, smooth(lt / dur))
    put_person(c, bx, 1000, 400, "carry", (lt * 0.7) % 1, rim=(255, 200, 170), side=1)
    return camera(c, lt, dur, 0.04)


# 42: reunion ---------------------------------------------------------

@lru_cache(None)
def reunion_layers():
    sky = grad(W, H, [(0, (8, 10, 26)), (1, (26, 20, 40))])

    def paint_wall(s):
        s.rect((0, 0, W, H), (92, 40, 32))
        s.rect((0, 0, W, 120), (60, 24, 20))
        s.rect((0, 700, W, H), (70, 30, 26))
    wall = static_layer(W, H, paint_wall)
    hole = Image.new("L", (W, H), 255)
    ImageDraw.Draw(hole).rounded_rectangle((520, 170, 1400, 620), 12, fill=0)
    wall.putalpha(hole)
    d = ImageDraw.Draw(wall)
    d.rectangle((520, 170, 1400, 184), fill=(130, 70, 40, 255))
    d.rectangle((952, 170, 968, 620), fill=(130, 70, 40, 255))
    d.rectangle((520, 606, 1400, 626), fill=(130, 70, 40, 255))
    for lx in (380, 1540):
        d.line((lx, 120, lx, 230), fill=(40, 20, 14, 255), width=3)
        d.ellipse((lx - 46, 230, lx + 46, 320), fill=(220, 40, 30, 255))
        d.rectangle((lx - 10, 320, lx + 10, 360), fill=(250, 200, 80, 255))
        glow(wall, lx, 275, 180, (255, 90, 60), 0.5)
    glow(wall, 960, 120, 700, (255, 190, 120), 0.35, 1.4)

    def paint_table(s):
        s.ellipse((260, 700, 1660, 930), (150, 26, 26))
        s.rect((260, 815, 1660, H), (120, 20, 22))
        s.ellipse((260, 690, 1660, 900), (180, 34, 32))
        for dx, dy, col in ((700, 760, (230, 220, 200)), (960, 740, (240, 180, 80)), (1220, 760, (230, 220, 200)),
                            (840, 820, (200, 100, 60)), (1080, 820, (120, 170, 90))):
            s.ellipse((dx - 80, dy - 24, dx + 80, dy + 24), (240, 236, 226))
            s.ellipse((dx - 60, dy - 16, dx + 60, dy + 14), col)
    table = static_layer(W, H, paint_table)
    return sky, wall, table


FIREWORKS = [(2.0, 700, 300, (255, 120, 90)), (3.4, 1220, 260, (255, 210, 110)), (9.5, 800, 280, (180, 160, 255)),
             (15.6, 960, 280, (255, 200, 120)), (16.2, 700, 330, (255, 120, 90)), (16.8, 1240, 300, (150, 220, 160)),
             (18.0, 860, 260, (255, 160, 200)), (19.4, 1120, 320, (255, 220, 140)), (21.0, 960, 300, (200, 180, 255))]


def scene_reunion(lt, dur):
    sky, wall, table = reunion_layers()
    c = sky.copy()
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for i, (t0, fx, fy, col) in enumerate(FIREWORKS):
        burst(ov, fx, fy, lt - t0, col, 72, 330, seed=i, life=2.2, size=4.5, gravity=90)
    snow(ov, W, H, lt, 70, 4, (520, 170, 1400, 620))
    c.alpha_composite(ov)
    for t0, fx, fy, col in FIREWORKS:
        a = clamp(1 - (lt - t0) / 1.2) if lt >= t0 else 0
        if a > 0:
            glow(c, fx, fy, 380, col, 0.55 * a)
    c.alpha_composite(wall)
    raise_p = smooth((lt - 4.6) / 1.6)
    speak_l = fade_window(lt, 7.6, 11.4, 0.6, 0.8)
    speak_r = fade_window(lt, 11.6, 15.4, 0.6, 0.8)
    glow(c, 760, 560, 300, HOME, 0.18 * speak_l)
    glow(c, 1160, 560, 300, CITY, 0.18 * speak_r)
    put_person(c, 780, 960, 470, "toast", raise_p, rim=(255, 200, 140), side=1)
    put_person(c, 1140, 960, 470, "toast", raise_p, rim=(255, 200, 140), side=-1)
    if lt > 6.2:
        clink = clamp(1 - (lt - 6.3) / 0.8)
        glow(c, 960, 548, 90, (255, 250, 220), 0.9 * clink)
    c.alpha_composite(table)
    glow(c, 960, 760, 600, (255, 180, 110), 0.18)
    return camera(c, lt, dur, 0.08, (0, -0.02))


def end_card(lt):
    c = Image.new("RGBA", (W, H), (6, 6, 10, 255))
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    motes(ov, W, H, lt, 70, 13, (255, 230, 200), (0, 120, W, 960))
    c.alpha_composite(ov)
    a = ease(lt / 1.0)
    draw_text(c, "如果回到 18 岁，", 960, 390, 70, (255, 255, 255), a)
    draw_text(c, "你会上车，还是留在站台？", 960, 490, 70, (255, 255, 255), a)
    b = ease((lt - 2.0) / 1.0)
    draw_text(c, "评论区，说说你的选择", 960, 620, 40, (252, 230, 190), b)
    e = ease((lt - 4.0) / 1.0)
    draw_text(c, "下一集  ·  考上大学  vs  早早打工", 960, 760, 38, (200, 200, 220), e)
    draw_text(c, "关注「两种人生」", 960, 830, 32, (160, 160, 185), e)
    return c


def title_card(lt):
    c = Image.new("RGBA", (W, H), (4, 4, 8, 255))
    glow(c, 960, 540, 800, (60, 50, 90), 0.5)
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    motes(ov, W, H, lt + 5, 80, 14, (255, 230, 200), (0, 120, W, 960))
    c.alpha_composite(ov)
    hit = ease(lt / 0.5)
    sc = lerp(1.25, 1.0, hit)
    draw_text(c, "两种人生  ·  第二集", 960, 360, 34, (200, 200, 220), ease((lt - 0.3) / 0.6))
    draw_text(c, "留下", 960 - 190 * sc, 530, 150, HOME, hit, scale=sc)
    draw_text(c, "/", 960, 530, 110, (120, 120, 140), hit, scale=sc)
    draw_text(c, "离开", 960 + 190 * sc, 530, 150, CITY, hit, scale=sc)
    draw_text(c, "留在老家  vs  去大城市", 960, 700, 42, (230, 230, 240), ease((lt - 0.8) / 0.8))
    flash = clamp(1 - lt / 0.35)
    if flash > 0:
        c.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(160 * flash))))
    return c


# ---------- composition ----------

def split(lt, dur, left, right):
    c = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    slide = ease(lt / 0.8)
    lx = int(lerp(-120, 0, slide))
    rx = int(lerp(HW + 120, HW, slide))
    c.alpha_composite(left, (max(0, lx), 0), (max(0, -lx), 0))
    c.alpha_composite(right.crop((0, 0, min(HW, W - rx), H)), (rx, 0))
    g = ease((lt - 0.2) / 0.8)
    ImageDraw.Draw(c).rectangle((HW - 1, int(540 - 420 * g), HW + 1, int(540 + 420 * g)), fill=(255, 255, 255, 200))
    glow(c, HW, 540, 140, (255, 255, 255), 0.12 * g)
    return c


CHAPTERS = [
    ("hook", 12.0, None),
    ("s23", 12.0, "23 岁"),
    ("s27", 13.0, "27 岁"),
    ("s31", 12.0, "31 岁"),
    ("s35", 23.0, "35 岁"),
    ("s39", 11.0, "39 岁"),
    ("s42", 25.0, "42 岁 · 春节"),
    ("end", 22.0, None),
]
SEGS = []
_t = 0.0
for _name, _d, _lab in CHAPTERS:
    SEGS.append((_name, _t, _d, _lab))
    _t += _d
TOTAL = _t

# (start, end, text, position, size, color)
SUBS = {
    "hook": [(0.3, 6.0, "18 岁，我们在这里分开。", "top", 64, (255, 255, 255)),
             (2.6, 6.0, "24 年后，我们对彼此说了同一句话。", "top2", 46, (255, 232, 200))],
    "s23": [(1.4, 11.6, "下班回家，饭是热的。", "L", 44, (255, 255, 255)),
            (4.6, 11.6, "凌晨一点，外卖是凉的。", "R", 44, (255, 255, 255))],
    "s27": [(1.4, 12.6, "他结婚了，村里摆了四十桌。", "L", 42, (255, 255, 255)),
            (5.0, 12.6, "她走了。这座城市，给不了他们一个家。", "R", 38, (255, 255, 255))],
    "s31": [(1.4, 11.6, "孩子，在爷爷奶奶身边长大。", "L", 42, (255, 255, 255)),
            (4.8, 11.6, "妈妈住不惯，总望着老家的方向。", "R", 40, (255, 255, 255))],
    "s35": [(0.6, 3.4, "凌晨三点，两个电话同时响起。", "C", 46, (255, 255, 255)),
            (4.6, 10.8, "他十分钟，就到了医院。", "L", 44, (255, 255, 255)),
            (6.6, 10.8, "他在高速上，开了九个小时。", "R", 44, (255, 255, 255)),
            (12.2, 15.6, "等他赶到，手术室的门已经关上了。", "C", 46, (255, 255, 255)),
            (16.4, 22.4, "钱，他挣到了。", "C2", 52, (255, 255, 255)),
            (18.6, 22.4, "可那一刻，他没赶上。", "C", 52, (255, 210, 200))],
    "s39": [(1.4, 10.6, "十年，工资涨了一千五。", "L", 44, (255, 255, 255)),
            (4.4, 10.6, "四十岁那年，他被裁了。", "R", 44, (255, 255, 255))],
    "s42": [(1.0, 4.4, "二十四年后，春节，同学聚会。", "C", 44, (255, 255, 255)),
            (7.6, 11.4, "“真羡慕你，见过那么大的世界。”", "C", 52, HOME),
            (11.6, 15.4, "“真羡慕你，一直守在爸妈身边。”", "C", 52, CITY),
            (16.6, 24.4, "原来，我们都活成了对方羡慕的样子。", "C", 54, (255, 236, 200))],
    "end": [(1.0, 10.6, "后来他们才明白——", "top", 50, (255, 255, 255)),
            (3.4, 10.6, "留下，不是没出息；离开，也不是不孝。", "top2", 44, (255, 236, 200)),
            (6.4, 10.6, "没有更好的路，只有自己选的路。", "C", 50, (255, 255, 255))],
}
POS = {"L": (HW / 2, 890), "R": (HW + HW / 2, 890), "C": (W / 2, 890), "C2": (W / 2, 820),
       "top": (W / 2, 250), "top2": (W / 2, 340)}

_post = {}


def post_fx(c, k):
    if "vig" not in _post:
        y, x = np.mgrid[0:H, 0:W]
        r = np.sqrt(((x - W / 2) / (W / 2)) ** 2 + ((y - H / 2) / (H / 2)) ** 2)
        _post["vig"] = np.clip(1 - 0.42 * np.clip(r - 0.45, 0, 1) ** 1.6, 0, 1).astype(np.float32)[..., None]
        rng = np.random.default_rng(0)
        _post["grain"] = [rng.normal(0, 4, (H, W, 1)).astype(np.float32) for _ in range(6)]
    arr = np.asarray(c.convert("RGB"), np.float32)
    arr = arr * _post["vig"] + _post["grain"][(k // 3) % 6]
    arr[:BAR] = 0
    arr[H - BAR:] = 0
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert("RGBA")


def render_chapter(name, lt, dur):
    if name == "hook":
        if lt < 6.2:
            return scene_station(lt, 6.2)
        if lt < 6.6:
            return Image.new("RGBA", (W, H), (0, 0, 0, 255))
        return title_card(lt - 6.6)
    if name == "s23":
        return split(lt, dur, half_kitchen(lt, dur), half_office(lt, dur))
    if name == "s27":
        return split(lt, dur, half_wedding(lt, dur), half_rental(lt, dur))
    if name == "s31":
        return split(lt, dur, half_river(lt, dur), half_balcony(lt, dur))
    if name == "s35":
        if lt < 3.6:
            return phones(lt)
        if lt < 11.4:
            st = lt - 3.6
            hrs = clamp(st / 7.2)
            mins = int(3 * 60 + 12 + hrs * (9 * 60 - 7))
            return split(st, 7.8, half_corridor(st, 7.8), half_highway(st, 7.8, f"{mins // 60:02d}:{mins % 60:02d}"))
        return scene_or(lt - 11.4, dur - 11.4)
    if name == "s39":
        return split(lt, dur, half_county(lt, dur), half_street(lt, dur))
    if name == "s42":
        return scene_reunion(lt, dur)
    if name == "end":
        if lt < 11.0:
            return scene_station(lt, 11.0, dawn=True)
        return end_card(lt - 11.0)


def frame_at(fi):
    t = fi / FPS
    for name, start, dur, label in SEGS:
        if t < start + dur:
            lt = t - start
            c = render_chapter(name, lt, dur)
            c = post_fx(c, fi)
            if label:
                la = fade_window(lt, 0.3, dur - 0.4, 0.8, 0.6)
                draw_text(c, label, W / 2, BAR / 2, 40, (235, 235, 245), la)
            if name in ("s23", "s27", "s31", "s39") or (name == "s35" and 3.6 <= lt < 11.4):
                la = fade_window(lt, 0.6, dur - 0.4, 0.8, 0.6)
                ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                od = ImageDraw.Draw(ov)
                for x0 in (40, HW + 40):
                    od.rounded_rectangle((x0, BAR + 22, x0 + 160, BAR + 68), 23, fill=(0, 0, 0, int(140 * la)))
                c.alpha_composite(ov)
                draw_text(c, "留下的他", 120, BAR + 44, 28, HOME, la)
                draw_text(c, "离开的他", HW + 120, BAR + 44, 28, CITY, la)
            for t0, t1, s, pos, size, col in SUBS.get(name, []):
                if t0 - 0.1 <= lt <= t1 + 0.6:
                    a = fade_window(lt, t0, t1, 0.45, 0.5)
                    blur = (1 - ease((lt - t0) / 0.45)) * 6
                    x, y = POS[pos]
                    draw_text(c, s, x, y + (1 - ease((lt - t0) / 0.5)) * 14, size, col, a, blur)
            fin = 0.02 if name in ("hook", "s35") else 0.5
            fout = 2.0 if name == "end" else 0.45
            a = min(ease(lt / fin), ease((dur - lt) / fout))
            rgb = c.convert("RGB")
            return rgb if a >= 0.999 else Image.blend(Image.new("RGB", (W, H)), rgb, a)
    return Image.new("RGB", (W, H))


# ---------- sound design ----------

def T(name):
    return [s for n, s, _, _ in SEGS if n == name][0]


def env_ad(n, a, d_):
    t = np.arange(n) / SR
    return np.minimum(1, t / max(a, 1e-4)) * np.exp(-np.maximum(0, t - a) * d_)


def sfx_whistle(dur=1.6):
    n = int(dur * SR)
    t = np.arange(n) / SR
    vib = 1 + 0.004 * np.sin(2 * np.pi * 5 * t)
    out = sum(np.sin(2 * np.pi * f * h * vib * t) / h ** 1.3 for f in (311.1, 370.0) for h in range(1, 6))
    env = np.minimum(1, t / 0.08) * np.minimum(1, (dur - t) / 0.4)
    return lowpass(out * env, 2500) / 3


def sfx_riser(dur=2.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    noise = np.random.default_rng(3).standard_normal(n)
    out = np.zeros(n)
    for i in range(8):
        seg = slice(i * n // 8, (i + 1) * n // 8)
        out[seg] = bandpass(noise[seg], 300 + i * 500, 900 + i * 900)
    f = 200 + 700 * (t / dur) ** 2
    out = out * 0.6 + 0.3 * np.sin(2 * np.pi * np.cumsum(f) / SR)
    return out * (t / dur) ** 2


def sfx_boom(dur=2.4):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = 62 * np.exp(-t * 1.2) + 30
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 1.6)
    hit = lowpass(np.random.default_rng(4).standard_normal(n), 900) * np.exp(-t * 14) * 0.8
    return sub + hit


def sfx_buzz(dur=0.45):
    n = int(dur * SR)
    t = np.arange(n) / SR
    base = np.sign(np.sin(2 * np.pi * 165 * t)) * 0.5 + np.sin(2 * np.pi * 165 * t)
    am = 0.6 + 0.4 * np.sin(2 * np.pi * 28 * t)
    return lowpass(base * am, 1200) * np.minimum(1, t / 0.02) * np.minimum(1, (dur - t) / 0.03)


def sfx_beep():
    n = int(0.14 * SR)
    t = np.arange(n) / SR
    return np.sin(2 * np.pi * 1046 * t) * np.minimum(1, t / 0.005) * np.minimum(1, (0.14 - t) / 0.02)


def sfx_sizzle(dur, rng):
    n = int(dur * SR)
    x = bandpass(rng.standard_normal(n), 2500, 9000)
    crack = (rng.random(n) < 0.002) * rng.uniform(1, 4, n)
    x = x * (0.4 + crack.cumsum() % 1 * 0.0) + bandpass(crack * rng.standard_normal(n), 2000, 8000) * 2
    return x / np.max(np.abs(x)) * np.minimum(1, np.minimum(np.arange(n), n - np.arange(n)) / SR)


def sfx_firecrackers(dur, rng, rate=24):
    n = int(dur * SR)
    out = np.zeros(n)
    t = 0.0
    while t < dur - 0.05:
        L = int(0.03 * SR)
        s = int(t * SR)
        pop = rng.standard_normal(L) * np.exp(-np.arange(L) / SR * 120)
        out[s:s + L] += pop * rng.uniform(0.4, 1.0)
        t += rng.exponential(1 / rate)
    return bandpass(out, 400, 9000)


def sfx_clink():
    n = int(2.2 * SR)
    t = np.arange(n) / SR
    out = sum(a * np.sin(2 * np.pi * f * t) * np.exp(-t * dc) for f, a, dc in
              ((2637, 1, 3.5), (3951, 0.6, 5), (5274, 0.35, 7), (6645, 0.2, 9)))
    return out * np.minimum(1, t / 0.001)


def sfx_firework(rng):
    n = int(2.4 * SR)
    t = np.arange(n) / SR
    boom = np.sin(2 * np.pi * np.cumsum(70 * np.exp(-t * 3) + 30) / SR) * np.exp(-t * 4)
    crackle = bandpass((rng.random(n) < 0.004) * rng.standard_normal(n), 2000, 9000) * 6
    crackle *= np.clip((t - 0.25) * 4, 0, 1) * np.exp(-np.maximum(0, t - 0.25) * 2)
    return boom * 0.9 + crackle


def sfx_murmur(dur, rng):
    n = int(dur * SR)
    x = bandpass(rng.standard_normal(n), 250, 2200)
    env = np.repeat(rng.uniform(0.3, 1.0, int(dur * 6) + 2), SR // 6)[:n]
    env = lowpass(env, 8)
    return x * env / np.max(np.abs(x * env))


def sfx_door():
    n = int(0.6 * SR)
    t = np.arange(n) / SR
    return (np.sin(2 * np.pi * 70 * t) * np.exp(-t * 14) +
            lowpass(np.random.default_rng(9).standard_normal(n), 600) * np.exp(-t * 30) * 0.5)


def sfx_page(rng):
    n = int(0.09 * SR)
    return bandpass(rng.standard_normal(n), 1500, 7000) * np.sin(np.linspace(0, np.pi, n))


def strings(chord_freqs, dur, attack=2.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    for f in chord_freqs:
        for det in (-0.004, 0, 0.004):
            ff = f * (1 + det)
            for h in range(1, 7):
                out += np.sin(2 * np.pi * ff * h * t + det * 100) / h
    out = lowpass(out, 1800)
    env = np.minimum(1, t / attack) * np.minimum(1, (dur - t) / 1.5)
    return out * env / (len(chord_freqs) * 3 * 2)


def keys(buf, t, names, vel=0.3, dur=2.6):
    for nm in names:
        place(buf, piano(note(nm), dur, vel), t)


def make_music(n):
    m = np.zeros((2, n))
    motif = [("E5", 0), ("D5", 0.5), ("C5", 1.0), ("G4", 2.0), ("A4", 3.0), ("C5", 3.5), ("D5", 4.5)]
    for nm, dt in motif:
        place(m, piano(note(nm), 3.0, 0.4), 0.6 + dt)
    beat = 60 / 70
    prog = [["C3", "G3", "E4"], ["G2", "D3", "B3"], ["A2", "E3", "C4"], ["F2", "C3", "A3"]]
    t = T("s23") - 0.3
    i = 0
    while t < T("s35"):
        ch = prog[i % 4]
        keys(m, t, [ch[0]], 0.4, 4)
        for j, nm in enumerate([ch[1], ch[2], ch[1], ch[2]]):
            place(m, piano(note(nm), 2.2, 0.22), t + j * beat)
        i += 1
        t += 4 * beat
    s35 = T("s35")
    tt = np.arange(int(20 * SR)) / SR
    drone = (np.sin(2 * np.pi * 55 * tt) + 0.5 * np.sin(2 * np.pi * 82.4 * tt)) * np.minimum(1, tt / 3) * np.minimum(1, (20 - tt) / 3)
    place(m, drone * 0.25, s35 + 3.0)
    for k, nm in enumerate(["A4", "E4", "C5", "B4", "A4"]):
        place(m, piano(note(nm), 4.0, 0.3), s35 + 12.0 + k * 2.2)
    t = T("s39")
    for k in range(3):
        ch = prog[(k + 2) % 4]
        keys(m, t + k * 4 * beat, [ch[0], ch[2]], 0.3, 4)
    s42 = T("s42")
    for k in range(2):
        keys(m, s42 + 0.5 + k * 3.0, ["A3", "E4", "C5"][k:k + 2], 0.25, 3)
    swell = s42 + 16.0
    chords = [[261.6, 329.6, 392.0], [196.0, 246.9, 293.7], [220.0, 261.6, 329.6], [174.6, 220.0, 261.6]]
    for k, chd in enumerate(chords * 2):
        st = swell + k * 2.6
        if st > T("end") + 11:
            break
        place(m, strings(chd, 3.2, 1.0 if k else 2.0) * 0.5, st)
        keys(m, st, [["C3", "G2", "A2", "F2"][k % 4]], 0.45, 3.5)
    mel = ["E5", "G5", "A5", "G5", "E5", "D5", "C5", "D5", "E5", "C5", "D5", "C5"]
    for k, nm in enumerate(mel):
        place(m, piano(note(nm), 3.0, 0.42), swell + 0.2 + k * 1.3)
    for nm, dt in motif:
        place(m, piano(note(nm), 3.5, 0.38), T("end") + 11.2 + dt)
    keys(m, T("end") + 17.0, ["C3", "G3", "E4", "C5"], 0.35, 5)
    for ch in range(2):
        m[ch] = reverb(m[ch], 2.8, 0.42, seed=ch + 1)
    return m


def make_audio(path):
    rng = np.random.default_rng(11)
    n = int(TOTAL * SR) + SR
    buf = np.zeros((2, n))
    mus = make_music(n)
    duck = np.ones(n)
    s42 = T("s42")
    a0, a1 = int((s42 + 6.0) * SR), int((s42 + 16.0) * SR)
    duck[a0:a1] = 0.08
    duck = lowpass(duck, 3)
    buf += mus / np.max(np.abs(mus)) * 0.42 * duck

    place(buf, sfx_whistle(), 0.0, 0.35)
    place(buf, reverb(sfx_whistle(), 2.0, 0.6), 0.0, 0.15)
    place(buf, sfx_train(rng, 6.2), 0.8, 0.30)
    place(buf, sfx_riser(1.8), 4.8, 0.22)
    place(buf, sfx_boom(), 6.6, 0.75)

    whoosh = sfx_whoosh(rng)
    for name, start, dur, _ in SEGS:
        if name not in ("hook", "s35"):
            place(buf, whoosh, start - 0.5, 0.18)

    s = T("s23")
    place(buf, sfx_sizzle(11, rng), s, 0.08, -0.6)
    place(buf, ambience_noise(rng, 11, 1500, 9000), s, 0.06, 0.6)
    for k in range(60):
        place(buf, sfx_click(rng), s + 2 + k * rng.uniform(0.09, 0.16), 0.10, 0.6)

    s = T("s27")
    place(buf, sfx_firecrackers(6, rng), s + 0.3, 0.16, -0.6)
    place(buf, sfx_murmur(10, rng), s, 0.05, -0.5)
    place(buf, sfx_door(), s + 7.6, 0.4, 0.6)

    s = T("s31")
    place(buf, ambience_noise(rng, 11, 100, 900), s, 0.06, -0.5)
    place(buf, ambience_noise(rng, 11, 300, 2000), s, 0.03, 0.6)

    s = T("s35")
    for k in range(4):
        place(buf, sfx_buzz(), s + 0.1 + k * 0.7, 0.35, -0.3)
        place(buf, sfx_buzz(), s + 0.12 + k * 0.7, 0.35, 0.3)
    for k in range(18):
        place(buf, sfx_heart(), s + 3.6 + k * 0.42, 0.35)
    place(buf, ambience_noise(rng, 7.8, 1500, 9000), s + 3.6, 0.07, 0.5)
    place(buf, ambience_noise(rng, 7.8, 60, 400), s + 3.6, 0.12, 0.5)
    for k in range(int(11.6 / 1.0)):
        place(buf, sfx_beep(), s + 11.6 + k * 1.0, 0.10)
    for k in range(10):
        place(buf, sfx_heart(), s + 11.6 + k * 1.1, 0.25 * (1 - k / 12))

    s = T("s39")
    for k in range(56):
        place(buf, sfx_page(rng), s + k / 8, 0.10, -0.6)
    place(buf, ambience_noise(rng, 10, 200, 1500), s, 0.06, 0.6)

    s = T("s42")
    mur = sfx_murmur(6.2, rng)
    place(buf, mur, s, 0.08)
    for t0, fx, fy, col in FIREWORKS:
        pan = (fx - 960) / 960
        place(buf, sfx_firework(rng), s + t0 - 0.05, 0.12 if t0 < 15 else 0.22, pan)
    place(buf, sfx_clink(), s + 6.3, 0.45)
    place(buf, reverb(sfx_clink(), 2.0, 0.6), s + 6.3, 0.2)

    e = T("end")
    place(buf, sfx_train(rng, 6), e + 2.0, 0.2)
    place(buf, sfx_whistle(1.2), e + 2.2, 0.15)
    place(buf, sfx_boom(1.8), e + 11.0, 0.25)

    buf /= max(1.0, np.max(np.abs(buf)) / 0.95)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((buf.T * 32767).astype(np.int16).tobytes())


# ---------- render ----------

def render_chunk(args):
    ci, f0, f1 = args
    out = f"{TMP}/chunk_{ci:02d}.mp4"
    proc = subprocess.Popen([
        "ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-c:v", "libx264", "-preset", "slow", "-crf", "20", "-maxrate", "5M", "-bufsize", "10M",
        "-pix_fmt", "yuv420p", "-threads", "1", out,
    ], stdin=subprocess.PIPE)
    for k in range(f0, f1):
        proc.stdin.write(frame_at(k).tobytes())
    proc.stdin.close()
    proc.wait()
    return out


def main():
    os.makedirs(TMP, exist_ok=True)
    frames = int(TOTAL * FPS)
    n_chunks = 16
    step = math.ceil(frames / n_chunks)
    jobs = [(i, i * step, min(frames, (i + 1) * step)) for i in range(n_chunks)]
    with Pool(int(sys.argv[1]) if len(sys.argv) > 1 else os.cpu_count()) as pool:
        audio = pool.apply_async(make_audio, (f"{TMP}/audio.wav",))
        chunks = pool.map(render_chunk, jobs)
        audio.get()
    with open(f"{TMP}/list.txt", "w") as f:
        f.writelines(f"file '{c}'\n" for c in chunks)
    out = f"{OUT_DIR}/ep2_hometown_vs_city.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", f"{TMP}/list.txt",
        "-i", f"{TMP}/audio.wav", "-c:v", "copy", "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
        "-ar", "44100", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", out,
    ], check=True)
    print(out, f"{TOTAL:.1f}s")


if __name__ == "__main__":
    main()
