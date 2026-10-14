import math
import os
import subprocess
import sys
import wave
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import make_video as base
from make_video import (ambience_noise, ctext, draw_person, ease, lowpass, mix, note, piano, place,
                        radial_bg, reverb, sfx_chime, sfx_click, sfx_heart, sfx_pop, sfx_tick,
                        sfx_train, sfx_whoosh, skyline, vgrad, wrap)

W, H, FPS, SR = 1080, 1920, 30, 44100
FONT = base.FONT
OUT_DIR = base.OUT_DIR
TMP = "/tmp/ep2_build"


def font(size):
    return ImageFont.truetype(FONT, size)


F = {k: font(v) for k, v in dict(
    hero=84, big=60, series=30, age=62, head=40, item=34, quote=32, cap=42, tag=28,
    card=44, cardsub=30, sub=40).items()}

HOME = (120, 196, 136)
CITY = (156, 146, 245)
PANEL = (24, 27, 40)
BG = (12, 13, 20)
TEXT = (232, 234, 242)
WARM = (252, 236, 200)

# (age, stage, home items, city items, home quote, city quote, caption, home tag, city tag, ambience)
SCENES = [
    (18, "高考后的路口",
     ["考上本省师范，离家四十分钟车程", "爸妈说：离家近，有个照应", "暑假跟着爸爸下地帮忙"],
     ["考去了一线城市的大学", "第一次坐高铁，箱子里塞满了辣酱", "站在地铁里，第一次觉得自己很渺小"],
     "送他去车站那天，我有点羡慕，也有点庆幸。",
     "车开动的时候，看着站台上的他，我突然很想下车。",
     "十八岁的路口，谁也不知道哪条路更好。", "安稳", "远方", "train"),
    (23, "第一份工作",
     ["考进县城编制，月薪四千五", "下班回家，妈妈已经做好了饭", "周末和老同学钓鱼、打牌"],
     ["进了互联网大厂，月薪两万", "合租十平米隔断间，月租三千五", "凌晨一点打车，前面还排着八十人"],
     "日子一眼能望到头，可那也是一种踏实。",
     "工资是他的四倍，可我很久没吃过一顿热饭了。",
     "一个用机会换安稳，一个用安稳换机会。", "踏实", "拼", "subway"),
    (27, "爱情与婚姻",
     ["亲戚介绍，相亲第三次就定了", "父母帮衬，县城买了一百四十平", "婚礼在村里摆了四十桌"],
     ["恋爱五年，因为买不起房分了手", "出租屋，已经搬了第四次", "每到春节，最怕被问“有对象没”"],
     "没有轰轰烈烈，但每天晚上，家里有人等我。",
     "她说：我们在这座城市，连一个家都没有。",
     "在大城市，爱情有时候输给了房价。", "成家", "漂泊", None),
    (31, "有了孩子",
     ["爷爷奶奶就住楼下，帮着带娃", "孩子上了县城最好的小学", "想报个编程课，整个县城都没有"],
     ["终于在五环外买了房，贷款三十年", "请不起阿姨，把妈妈从老家接来", "孩子的同学，周末都在学马术"],
     "孩子很快乐，可我怕他和我一样，看不到更大的世界。",
     "妈妈住不惯，每天站在阳台上，望着老家的方向。",
     "每一代人的选择，最后都落在下一代身上。", "陪伴", "起点", None),
    (35, "父亲病倒",
     ["爸爸半夜心梗，他十分钟就赶到了医院", "县医院条件有限，连夜转去省城", "那一年，他在病床边守了两个月"],
     ["接到电话时，他正在开一个重要的会", "抢不到票，在高速上开了九个小时", "赶到时，爸爸已经推进了手术室"],
     "那天我第一次庆幸，自己一直在他身边。",
     "我挣了很多钱，却没赶上爸爸最需要我的那一刻。",
     "父母在，人生尚有来处。", "守候", "亏欠", "heart"),
    (39, "中年",
     ["单位效益一般，十年工资涨了一千五", "身边人都差不多，没人焦虑也没人冒尖", "刷到他的朋友圈，会想：如果当年……"],
     ["公司裁员，名单上有他", "房贷还剩二十年，每月一万二", "投了一百份简历，回复不到十个"],
     "我好像没输过，可也从来没赢过。",
     "我以为自己属于这座城市，可这座城市不属于任何人。",
     "没有哪一条路，是一直坦途。", "平淡", "失去", "rain"),
    (42, "春节同学聚会",
     ["他做东，订了镇上最好的包间", "房贷早还完了，孩子上了初中", "酒过三巡，他红着眼说了一句话"],
     ["他开着车，回到了阔别的老家", "鬓角白了，酒量却大了", "碰杯的时候，他也说了一句话"],
     "真羡慕你，见过那么大的世界。",
     "真羡慕你，一直守在爸妈身边。",
     "原来，我们都活成了对方羡慕的样子。", "羡慕", "羡慕", None),
    (46, "各自的答案",
     ["他教的学生，有人考去了北京", "每天傍晚，陪爸妈在河边散步", "他终于明白：安稳不是平庸"],
     ["回到省城，重新开了间小公司", "把爸妈接到身边，每周一起吃饭", "他终于明白：远方不是逃离"],
     "我守住了根。",
     "我看过了远方。",
     "没有标准答案，只有各自的答案。", "根", "远方", "clock"),
]

SKY = [
    ((255, 196, 160), (140, 150, 210)), ((150, 200, 245), (90, 150, 220)),
    ((120, 185, 245), (70, 130, 210)), ((170, 200, 240), (100, 140, 200)),
    ((70, 70, 110), (25, 25, 50)), ((250, 160, 100), (150, 80, 110)),
    ((30, 34, 70), (10, 12, 30)), ((255, 180, 120), (190, 110, 120)),
]

INTRO_D, SCENE_D, SUMMARY_D, END_D = 8.0, 16.0, 19.0, 12.0
ITEM_T = [1.2, 2.4, 3.6]
HQ_T, CQ_T, CAP_T = 5.0, 8.4, 12.2
CPS = 10.0

CARDS = [
    ("留下，不是没出息；", "离开，也不是不孝顺。"),
    ("大城市给你机会，", "小城给你温度。"),
    ("哪条路都有遗憾，", "重要的是，别辜负自己的选择。"),
]
CARD_T = [1.5, 6.5, 11.5]

SEGS = []
_t = 0.0
for kind, d, idx in [("intro", INTRO_D, None)] + [("scene", SCENE_D, i) for i in range(len(SCENES))] + \
        [("summary", SUMMARY_D, None), ("end", END_D, None)]:
    SEGS.append((kind, _t, d, idx))
    _t += d
TOTAL = _t

PX, PW = 40, 1000
PANELS = [(190, 850), (870, 1530)]
BAN = (20, 78, 960, 280)


# ---------- illustrations (2x supersampled) ----------

def hometown_view(d, x0, y0, x1, y1, rng, sky_bot, night, k):
    hill = tuple(int(c * 0.55 + g) for c, g in zip(sky_bot, (0, 25, 0)))
    pts = [(x0, y1)]
    for x in range(x0, x1 + 1, 8 * k):
        pts.append((x, y0 + (y1 - y0) * (0.45 + 0.1 * math.sin(x / (60 * k) + rng.random()))))
    pts.append((x1, y1))
    d.polygon(pts, fill=hill)
    near = tuple(max(0, c - 20) for c in hill)
    pts = [(x0, y1)] + [(x, y0 + (y1 - y0) * (0.68 + 0.05 * math.sin(x / (35 * k)))) for x in range(x0, x1 + 1, 8 * k)] + [(x1, y1)]
    d.polygon(pts, fill=near)
    for _ in range(7):
        hx = rng.integers(x0, x1 - 50 * k)
        hy = y0 + (y1 - y0) * rng.uniform(0.66, 0.8)
        hw = rng.integers(36, 60) * k
        hh = hw * 0.55
        wall = (200, 196, 186) if not night else (90, 90, 100)
        d.rectangle((hx, hy, hx + hw, hy + hh), fill=wall)
        d.polygon([(hx - 5 * k, hy), (hx + hw / 2, hy - hh * 0.6), (hx + hw + 5 * k, hy)], fill=(150, 70, 60) if not night else (60, 40, 40))
        wc = (255, 210, 120) if night else (90, 110, 130)
        d.rectangle((hx + hw * 0.35, hy + hh * 0.3, hx + hw * 0.6, hy + hh * 0.7), fill=wc)
    for _ in range(6):
        tx = rng.integers(x0, x1)
        ty = y0 + (y1 - y0) * rng.uniform(0.7, 0.85)
        r = rng.integers(12, 20) * k
        d.rectangle((tx - 2 * k, ty, tx + 2 * k, ty + r), fill=(80, 60, 40))
        d.ellipse((tx - r, ty - r * 1.4, tx + r, ty + r * 0.4), fill=(70, 130, 80) if not night else (30, 50, 40))


def banner(idx, city, bw, bh):
    k = 2
    age = SCENES[idx][0]
    sky_top, sky_bot = SKY[idx]
    night = idx in (4, 6)
    w, h = bw * k, bh * k
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    wall = (52, 56, 72) if city else (84, 70, 58)
    floor = (96, 98, 108) if city else (110, 80, 58)
    floor_y = int(h * 0.82)
    d.rectangle((0, 0, w, h), fill=wall)
    d.rectangle((0, floor_y, w, h), fill=floor)
    rng = np.random.default_rng(100 + idx * 3 + city)
    if city:
        wx0, wy0, wx1, wy1 = int(w * 0.42), int(h * 0.10), int(w * 0.70), int(h * 0.66)
    else:
        wx0, wy0, wx1, wy1 = int(w * 0.38), int(h * 0.12), int(w * 0.86), int(h * 0.64)
    img.paste(vgrad(wx1 - wx0, wy1 - wy0, sky_top, sky_bot), (wx0, wy0))
    if night:
        for _ in range(30):
            sx, sy = rng.integers(wx0, wx1), rng.integers(wy0, wy0 + (wy1 - wy0) // 2)
            d.ellipse((sx, sy, sx + 3 * k, sy + 3 * k), fill=(240, 240, 255))
    if city:
        sil = tuple(int(c * 0.4) for c in sky_bot)
        win_h = (wy1 - wy0) // k
        skyline(d, wx0, wy1, wx1, rng, win_h // 3, win_h - 12, 14, 30, sil, True, k)
        frame = (70, 74, 88)
    else:
        hometown_view(d, wx0, wy0, wx1, wy1, rng, sky_bot, night, k)
        frame = (130, 104, 78)
    d.rectangle((wx0, wy0, wx1, wy1), outline=frame, width=8 * k)
    d.line(((wx0 + wx1) // 2, wy0, (wx0 + wx1) // 2, wy1), fill=frame, width=6 * k)
    d.rectangle((wx0 - 10 * k, wy1, wx1 + 10 * k, wy1 + 10 * k), fill=frame)
    if city:
        d.rectangle((int(w * 0.76), floor_y - 70 * k, w, floor_y), fill=(70, 80, 110))
        d.rectangle((int(w * 0.76), floor_y - 90 * k, int(w * 0.82), floor_y - 40 * k), fill=(200, 200, 210))
        d.rectangle((int(w * 0.3), floor_y - 64 * k, int(w * 0.4), floor_y), fill=(60, 60, 70))
        d.polygon([(int(w * 0.31), floor_y - 64 * k), (int(w * 0.39), floor_y - 64 * k),
                   (int(w * 0.38), floor_y - 94 * k), (int(w * 0.32), floor_y - 94 * k)], fill=(150, 200, 255))
    else:
        d.rounded_rectangle((int(w * 0.88), floor_y - 60 * k, int(w * 0.98), floor_y), 6 * k, fill=(130, 96, 66))
        d.ellipse((int(w * 0.9), floor_y - 100 * k, int(w * 0.96), floor_y - 56 * k), fill=(80, 150, 90))
        d.rectangle((int(w * 0.6), floor_y - 50 * k, int(w * 0.8), floor_y - 40 * k), fill=(140, 100, 70))
        d.rectangle((int(w * 0.62), floor_y - 40 * k, int(w * 0.63), floor_y), fill=(140, 100, 70))
        d.rectangle((int(w * 0.77), floor_y - 40 * k, int(w * 0.78), floor_y), fill=(140, 100, 70))
        d.ellipse((int(w * 0.66), floor_y - 70 * k, int(w * 0.70), floor_y - 50 * k), fill=(220, 220, 210))
    light = Image.new("L", (w, h), 0)
    ImageDraw.Draw(light).ellipse((wx0 - 200 * k, wy0, wx1 + 100 * k, h + 200 * k), fill=50 if not night else 25)
    light = light.filter(ImageFilter.GaussianBlur(60 * k))
    img = Image.composite(Image.new("RGB", (w, h), sky_top), img, light)
    shadow = Image.new("L", (w, h), 0)
    pcx = int(w * 0.16)
    ImageDraw.Draw(shadow).ellipse((pcx - 80 * k, floor_y + 18 * k, pcx + 80 * k, floor_y + 40 * k), fill=90)
    img = Image.composite(Image.new("RGB", (w, h)), img, shadow.filter(ImageFilter.GaussianBlur(8 * k)))
    draw_person(ImageDraw.Draw(img), pcx, floor_y + 30 * k, age, CITY if city else HOME, k)
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rectangle((0, 0, w, h), outline=110, width=40 * k)
    img = Image.composite(Image.new("RGB", (w, h)), img, mask.filter(ImageFilter.GaussianBlur(30 * k)))
    img = img.resize((bw, bh), Image.LANCZOS)
    rmask = Image.new("L", (bw, bh), 0)
    ImageDraw.Draw(rmask).rounded_rectangle((0, 0, bw - 1, bh - 1), 18, fill=255)
    return img, rmask


def series_chip(d, y, a, bg):
    s = "两种人生 · 第二集"
    tw = d.textlength(s, font=F["series"]) + 40
    d.rounded_rectangle((W / 2 - tw / 2, y, W / 2 + tw / 2, y + 48), 24, outline=mix((200, 200, 220), bg, a * 0.6), width=2)
    ctext(d, W / 2, y + 6, s, F["series"], mix((200, 200, 220), bg, a))


_cache = {}


def scene_base(idx):
    if idx not in _cache:
        img = vgrad(W, H, (20, 23, 36), BG)
        d = ImageDraw.Draw(img)
        for side, (y0, y1) in enumerate(PANELS):
            col = CITY if side else HOME
            d.rounded_rectangle((PX, y0, PX + PW, y1), 28, fill=PANEL, outline=tuple(int(c * 0.55) for c in col), width=2)
            b, m = banner(idx, side, BAN[2], BAN[3])
            img.paste(b, (PX + BAN[0], y0 + BAN[1]), m)
        _cache[idx] = img
    return _cache[idx]


def draw_scene(idx, lt):
    age, stage, hitems, citems, hq, cq, cap, htag, ctag = SCENES[idx][:9]
    img = scene_base(idx).copy()
    d = ImageDraw.Draw(img)
    prog = (idx + lt / SCENE_D) / len(SCENES)
    d.rectangle((0, 0, W, 6), fill=(36, 40, 58))
    d.rectangle((0, 0, int(W * prog), 6), fill=(170, 180, 240))
    series_chip(d, 30, 1, BG)
    ctext(d, W / 2, 92, f"{age} 岁 · {stage}", F["age"], TEXT)
    for side, (y0, y1) in enumerate(PANELS):
        col = CITY if side else HOME
        title = "去了大城市的他" if side else "留在老家的他"
        items, quote, tag = (citems, cq, ctag) if side else (hitems, hq, htag)
        d.text((PX + 30, y0 + 16), title, font=F["head"], fill=col)
        tp = ease((lt - 0.6) / 0.6)
        if tp > 0:
            tw = d.textlength(tag, font=F["tag"]) + 36
            tx, ty = PX + PW - 30 - tw, y0 + 20
            d.rounded_rectangle((tx, ty, tx + tw, ty + 42), 21, fill=mix(col, PANEL, 0.25 * tp), outline=mix(col, PANEL, tp), width=2)
            d.text((tx + 18, ty + 4), tag, font=F["tag"], fill=mix(col, PANEL, tp))
        for i, s in enumerate(items):
            p = ease((lt - ITEM_T[i]) / 0.6)
            if p > 0:
                y = y0 + 378 + i * 54
                tx = PX + 64 + (1 - p) * 40
                d.ellipse((tx - 26, y + 14, tx - 14, y + 26), fill=mix(col, PANEL, p))
                d.text((tx, y), s, font=F["item"], fill=mix(TEXT, PANEL, p))
        qs = CQ_T if side else HQ_T
        if lt >= qs - 0.4:
            qy = y0 + 548
            qp = ease((lt - qs + 0.4) / 0.4)
            d.rounded_rectangle((PX + 28, qy, PX + PW - 28, y1 - 20), 18, fill=mix((34, 38, 56), PANEL, qp))
            d.rectangle((PX + 28, qy + 14, PX + 34, y1 - 34), fill=mix(col, PANEL, qp))
            n = int(max(0.0, lt - qs) * CPS)
            done = n >= len(quote)
            lines = wrap(d, "“" + quote + "”", F["quote"], PW - 130)
            remaining = min(n, len(quote)) + 1 + (1 if done else 0)
            for li, line in enumerate(lines):
                part = line[:max(0, remaining)]
                remaining -= len(line)
                if part:
                    d.text((PX + 64, qy + 18 + li * 44), part, font=F["quote"], fill=WARM)
    cp = ease((lt - CAP_T) / 0.8)
    if cp > 0:
        d.rounded_rectangle((60, 1560, W - 60, 1670), 26, fill=mix((30, 33, 50), BG, cp))
        ctext(d, W / 2, 1588, cap, F["cap"], mix(WARM, BG, cp))
    return img


_intro = None


def intro_base():
    global _intro
    if _intro is None:
        k = 2
        img = radial_bg((34, 32, 56), (6, 6, 12)).resize((W * k, H * k))
        d = ImageDraw.Draw(img)
        cx, by, fy = W * k // 2, 1650 * k, 1150 * k
        road = (60, 62, 80)
        d.polygon([(cx - 160 * k, by), (cx + 160 * k, by), (cx + 40 * k, 1380 * k), (cx - 40 * k, 1380 * k)], fill=road)
        d.polygon([(cx - 40 * k, 1380 * k), (cx, 1380 * k), (cx - 300 * k, fy), (cx - 340 * k, fy)], fill=road)
        d.polygon([(cx, 1380 * k), (cx + 40 * k, 1380 * k), (cx + 340 * k, fy), (cx + 300 * k, fy)], fill=road)
        rng = np.random.default_rng(7)
        for i in range(5):
            hx = cx - 480 * k + i * 70 * k
            d.rectangle((hx, fy - 40 * k, hx + 50 * k, fy), fill=(70, 110, 80))
            d.polygon([(hx - 6 * k, fy - 40 * k), (hx + 25 * k, fy - 64 * k), (hx + 56 * k, fy - 40 * k)], fill=(120, 80, 70))
            d.rectangle((hx + 18 * k, fy - 28 * k, hx + 32 * k, fy - 14 * k), fill=(255, 210, 120))
        skyline(d, cx + 200 * k, fy, cx + 520 * k, rng, 80, 260, 20, 40, (60, 56, 110), True, k)
        draw_person(d, cx - 40 * k, 1560 * k, 18, HOME, k)
        draw_person(d, cx + 40 * k, 1560 * k, 18, CITY, k)
        _intro = img.resize((W, H), Image.LANCZOS)
    return _intro


def draw_intro(lt):
    img = intro_base().copy()
    d = ImageDraw.Draw(img)
    bg = (22, 22, 38)
    ctext(d, W / 2, 230, "18 岁那年，", F["big"], TEXT)
    ctext(d, W / 2, 320, "我们站在了同一个路口。", F["big"], TEXT)
    p = ease((lt - 2.2) / 0.8)
    ctext(d, W / 2, 450, "一个留了下来，一个去了远方。", F["sub"], mix(WARM, bg, p))
    q = ease((lt - 4.0) / 0.8)
    if q > 0:
        series_chip(d, 600, q, bg)
        ctext(d, W / 2, 680, "留在老家  vs  去大城市", F["hero"], mix((255, 255, 255), bg, q))
    return img


def draw_summary(lt):
    img = vgrad(W, H, (18, 20, 34), (8, 8, 14))
    d = ImageDraw.Draw(img)
    bg = (14, 15, 25)
    p = ease(lt / 1.0)
    ctext(d, W / 2, 260, "写在最后", F["big"], mix(WARM, bg, p))
    d.rectangle((W / 2 - 60, 350, W / 2 + 60, 354), fill=mix(WARM, bg, p))
    for i, (h1, h2) in enumerate(CARDS):
        q = ease((lt - CARD_T[i]) / 1.0)
        if q <= 0:
            continue
        y = 440 + i * 300 + (1 - q) * 30
        d.rounded_rectangle((70, y, W - 70, y + 250), 26, fill=mix((30, 33, 52), bg, q))
        d.rounded_rectangle((70, y, 82, y + 250), 6, fill=mix([HOME, CITY, (240, 170, 120)][i], bg, q))
        d.text((130, y + 60), h1, font=F["card"], fill=mix((255, 255, 255), bg, q))
        d.text((130, y + 140), h2, font=F["card"], fill=mix(WARM, bg, q))
    return img


def draw_end(lt):
    img = Image.new("RGB", (W, H), (8, 8, 14))
    d = ImageDraw.Draw(img)
    bg = (8, 8, 14)
    a = ease(lt / 1.0)
    ctext(d, W / 2, 520, "如果回到 18 岁，", F["big"], mix((255, 255, 255), bg, a))
    ctext(d, W / 2, 610, "你会留下，还是离开？", F["big"], mix((255, 255, 255), bg, a))
    b = ease((lt - 2.0) / 1.0)
    ctext(d, W / 2, 740, "评论区，说说你的选择", F["sub"], mix(WARM, bg, b))
    c = ease((lt - 4.5) / 1.0)
    if c > 0:
        d.rounded_rectangle((140, 960, W - 140, 1160), 26, fill=mix((30, 33, 52), bg, c))
        ctext(d, W / 2, 990, "下一集预告", F["tag"], mix((180, 184, 210), bg, c))
        ctext(d, W / 2, 1050, "考上大学 vs 早早打工", F["card"], mix((255, 255, 255), bg, c))
    e = ease((lt - 6.5) / 1.0)
    ctext(d, W / 2, 1260, "关注「两种人生」，看见每一种人生", F["cardsub"], mix((200, 200, 220), bg, e))
    return img


def frame_at(t):
    for kind, start, dur, idx in SEGS:
        if t < start + dur:
            lt = t - start
            fn = {"intro": draw_intro, "summary": draw_summary, "end": draw_end}.get(kind)
            img = draw_scene(idx, lt) if kind == "scene" else fn(lt)
            fin = 0.01 if kind == "intro" else 0.5
            fout = 2.5 if kind == "end" else 0.6
            a = min(ease(lt / fin), ease((dur - lt) / fout))
            return img if a >= 1 else Image.blend(Image.new("RGB", (W, H)), img, a)
    return Image.new("RGB", (W, H))


# ---------- audio ----------

def make_music():
    n = int(TOTAL * SR) + SR
    mus = np.zeros(n)
    beat = 60 / 72
    prog = [("C3", ["C4", "G4", "E4", "G4"]), ("G2", ["B3", "G4", "D4", "G4"]),
            ("A2", ["C4", "A4", "E4", "A4"]), ("E2", ["B3", "G4", "E4", "G4"]),
            ("F2", ["C4", "A4", "F4", "A4"]), ("C3", ["C4", "G4", "E4", "G4"]),
            ("F2", ["C4", "A4", "F4", "A4"]), ("G2", ["B3", "G4", "D4", "G4"])]
    melody = ["E5", "D5", "C5", "D5", "E5", None, "G5", None, "A5", "G5", "E5", None, "D5", None, None, None,
              "C5", "D5", "E5", None, "G5", "E5", "D5", None, "C5", None, "D5", None, "C5", None, None, None]
    reunion = [s for k, s, _, i in SEGS if k == "scene" and i == 6][0]
    t, bar = 0.3, 0
    while t < TOTAL - 4:
        bass, arp = prog[bar % 8]
        si = int(t * SR)
        sig = piano(note(bass), 2 * beat + 2, 0.5) + piano(note(bass) * 2, 2 * beat + 2, 0.2)
        mus[si:si + len(sig)] += sig[:n - si]
        for j, nm in enumerate(arp):
            s = piano(note(nm), 2.2, 0.3 if j % 2 == 0 else 0.22)
            sj = int((t + j * beat / 2) * SR)
            mus[sj:sj + len(s)] += s[:n - sj]
        if t >= reunion - 1:
            for j in range(4):
                nm = melody[(bar % 8) * 4 + j]
                if nm:
                    s = piano(note(nm), 2.8, 0.45)
                    sj = int((t + j * beat / 2) * SR)
                    mus[sj:sj + len(s)] += s[:n - sj]
        bar += 1
        t += 2 * beat
    tt = np.arange(n) / SR
    pad = np.zeros(n)
    m = tt >= reunion - 2
    for f in [261.6, 329.6, 392.0]:
        pad[m] += np.sin(2 * np.pi * f * tt[m]) * 0.05
    pad = lowpass(pad, 900) * np.clip((tt - reunion + 2) / 5, 0, 1)
    mus = reverb(mus + pad, 2.6, 0.4, seed=3)
    return mus * np.clip(tt / 0.5, 0, 1) * np.clip((TOTAL - tt) / 6, 0, 1)


def make_audio(path):
    rng = np.random.default_rng(7)
    n = int(TOTAL * SR) + SR
    buf = np.zeros((2, n))
    mus = make_music()
    buf += mus / np.max(np.abs(mus)) * 0.38
    whoosh, chime = sfx_whoosh(rng), sfx_chime()
    place(buf, chime, 0.05, 0.10)
    place(buf, sfx_pop(520), 2.2, 0.12)
    place(buf, chime, 4.0, 0.08)
    for kind, start, dur, idx in SEGS:
        if kind != "intro":
            place(buf, whoosh, start - 0.55, 0.16)
        if kind == "scene":
            sc = SCENES[idx]
            for side, pan in ((0, -0.4), (1, 0.4)):
                for it in ITEM_T:
                    place(buf, sfx_pop(760 if side == 0 else 1020), start + it + side * 0.1, 0.10, pan)
                qs, q = (CQ_T, sc[5]) if side else (HQ_T, sc[4])
                for c in range(len(q)):
                    place(buf, sfx_click(rng), start + qs + c / CPS, 0.09 * rng.uniform(0.6, 1.0), pan)
            place(buf, chime, start + CAP_T, 0.07)
            amb = sc[9]
            if amb == "train":
                place(buf, sfx_train(rng, 8), start, 0.18)
            elif amb == "subway":
                place(buf, ambience_noise(rng, dur, 80, 600), start, 0.10)
            elif amb == "heart":
                for b in range(10):
                    place(buf, sfx_heart(), start + 0.4 + b * 0.75, 0.32)
                place(buf, ambience_noise(rng, dur, 1500, 9000), start, 0.04)
            elif amb == "rain":
                place(buf, ambience_noise(rng, dur, 1500, 9000), start, 0.05, -0.1)
                place(buf, ambience_noise(rng, dur, 1500, 9000), start, 0.05, 0.1)
            elif amb == "clock":
                for b in range(int(dur)):
                    place(buf, sfx_tick(b % 2 == 0), start + b + 0.2, 0.10)
        elif kind == "summary":
            for ct in CARD_T:
                place(buf, sfx_pop(520), start + ct, 0.12)
        elif kind == "end":
            place(buf, chime, start + 4.5, 0.08)
    buf /= max(1.0, np.max(np.abs(buf)) / 0.95)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((buf.T * 32767).astype(np.int16).tobytes())


def render_chunk(args):
    ci, f0, f1 = args
    out = f"{TMP}/chunk_{ci:02d}.mp4"
    proc = subprocess.Popen([
        "ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p", "-threads", "1", out,
    ], stdin=subprocess.PIPE)
    for k in range(f0, f1):
        proc.stdin.write(frame_at(k / FPS).tobytes())
    proc.stdin.close()
    proc.wait()
    return out


def main():
    os.makedirs(TMP, exist_ok=True)
    frames = int(TOTAL * FPS)
    step = math.ceil(frames / 12)
    jobs = [(i, i * step, min(frames, (i + 1) * step)) for i in range(12)]
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
