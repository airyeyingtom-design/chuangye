import math
import os
import subprocess
import sys
import wave
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1920, 1080, 30
SR = 44100
FONT = "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"
OUT_DIR = os.path.dirname(os.path.abspath(__file__))
TMP = "/tmp/two_lives_build"


def font(size):
    return ImageFont.truetype(FONT, size)


F = {k: font(v) for k, v in dict(
    hero=96, title=64, sub=40, age=58, head=38, item=33, quote=31,
    cap=40, tag=28, small=24, card=46, cardsub=30).items()}

POOR = (100, 158, 222)
RICH = (226, 182, 86)
PANEL = (24, 27, 40)
BG = (12, 13, 20)
TEXT = (232, 234, 242)
WARM = (252, 236, 200)

# (age, stage, poor items, rich items, poor quote, rich quote, caption, poor tag, rich tag, ambience, desk)
SCENES = [
    (0, "出生",
     ["县医院走廊加床，三人一间", "爸爸在缴费窗口把钱数了三遍", "外婆连夜坐绿皮火车赶来"],
     ["私立医院套房，月子中心 28 天", "名字请人算过，早教课排到 3 岁", "满月酒请了三百位宾客"],
     "妈妈说，我出生那天，爸爸笑得像个孩子。",
     "妈妈说，我出生那天，爸爸推掉了一个重要会议。",
     "起点不一样，但那一刻的欢喜，一模一样。", "省", "备", "heart", False),
    (4, "童年",
     ["爸妈在外打工，跟着奶奶在老家", "一年只在春节见爸妈一次", "最爱的玩具，是爸爸做的木头车"],
     ["双语幼儿园，学费一年十几万", "钢琴、马术、乐高机器人", "爸妈常出差，陪着的是育儿嫂"],
     "过年最怕的是初六，爸妈又要走了。",
     "我有一整屋的玩具，可我只想妈妈陪我搭积木。",
     "孩子不懂钱，他们只记得谁陪在身边。", "想念", "孤单", None, False),
    (8, "小学",
     ["公立小学，一个班五十二个人", "脖子上挂着钥匙，自己回家", "作文《我的理想》：当一名老师"],
     ["国际学校小班，外教授课", "司机接送，晚上还有私教", "作文 My Dream：当宇航员"],
     "同学有新文具盒，我说我不喜欢。其实我很喜欢。",
     "我去过二十个国家，却记不住同桌的名字。",
     "差距，开始从“见过多少世界”里长出来。", "懂事", "见识", "bell", True),
    (13, "初中",
     ["第一次知道什么叫“学区房”", "周末补习班，是妈妈加班两个月换的", "生日愿望：爸妈别再为钱吵架"],
     ["寒暑假去海外夏校、竞赛集训", "升学路径早已规划好", "成绩不好，就换一个更贵的老师"],
     "我开始懂事了。懂事，就是不再开口要东西。",
     "爸爸说：你什么都不缺，凭什么考不好？",
     "一个在学着体谅，一个在学着承受期待。", "体谅", "期待", None, True),
    (17, "高中",
     ["高考是唯一的路，凌晨一点还在刷题", "黑板角落写着“距离高考 100 天”", "每次月考成绩，妈妈都存在手机里"],
     ["留学顾问全程规划，背景提升", "申请文书，请专人一遍遍打磨", "可以选喜欢的专业，而非“好就业”"],
     "我不敢失败。我输不起，我家也输不起。",
     "我可以失败。可我不知道自己真正想要什么。",
     "一个没有退路，一个有太多条路。", "拼", "选", "clock", True),
    (18, "离家上大学",
     ["录取通知书到的那天，村口放了鞭炮", "申请助学贷款，周末去做家教", "第一次坐飞机，是大三去外地面试"],
     ["收到海外名校录取，一年花费几十万", "不用打工，去非洲做了志愿者", "暑假在家里朋友的投行实习"],
     "爸爸第一次在我面前哭，是在送我的火车站。",
     "在异国的公寓里，我第一次学会自己煮面。",
     "离家那天，两个家庭都红了眼眶。", "离家", "远行", "train", False),
    (24, "初入职场",
     ["投了两百份简历，进了一家小公司", "合租城中村，通勤一个半小时", "月薪六千，每月给家里打两千"],
     ["进家族企业，或拿家里的钱创业", "住在父母买的市中心公寓", "第一次创业失败，亏掉三百万"],
     "加班到深夜，地铁窗外万家灯火，没有一盏是我的。",
     "爸爸说就当交学费。可我知道，大家都在看我是不是只能靠家里。",
     "试错的成本，决定了一个人敢不敢冒险。", "扛", "证明", "subway", False),
    (30, "成家",
     ["两家六个钱包，凑齐了首付", "背上三十年房贷，每月还八千", "婚礼上，妈妈偷偷塞来一张存折"],
     ["婚前协议，资产做好隔离", "海岛婚礼，宾客三百人", "婚房是父母送的别墅"],
     "拿到钥匙那天，我们坐在毛坯房里，吃了一碗泡面。",
     "婚礼很盛大，我却总在想：她爱的是我，还是我的家？",
     "家，对一个是终点线，对另一个是新起点。", "安家", "真心", None, False),
    (42, "中年",
     ["上有四位老人，下有一个孩子", "过了三十五岁，最怕听到“优化”", "爸爸住院，在走廊里算医保能报多少"],
     ["接手家族生意，压力不比谁小", "体检报告比财报更让人焦虑", "和孩子的对话，越来越像开会"],
     "我不敢生病，不敢辞职，不敢停下来。",
     "我拥有很多，却越来越害怕失去。",
     "人到中年，每个人都在负重前行。", "撑", "守", "rain", False),
    (68, "晚年",
     ["退休金每月三千五，省着够用", "每天接孙子放学，路上讲过去的事", "孩子在城里有了房，他终于松了口气"],
     ["高端养老社区，私人医生", "家族信托，安排好财富传承", "子女在世界各地，视频比见面多"],
     "这辈子没大富大贵，但孩子过得比我好，值了。",
     "我留下了一份很大的家业。希望留下的，不只是钱。",
     "走到最后，健康、陪伴和问心无愧，比什么都重要。", "值得", "传承", "clock", False),
]

SKY = [  # dawn -> night, one per scene
    ((255, 176, 150), (120, 110, 170)), ((255, 210, 170), (130, 170, 220)),
    ((150, 200, 245), (90, 150, 220)), ((120, 185, 245), (70, 130, 210)),
    ((110, 175, 240), (60, 115, 200)), ((160, 190, 230), (90, 120, 190)),
    ((255, 190, 120), (200, 110, 110)), ((250, 150, 90), (140, 70, 110)),
    ((150, 90, 130), (50, 40, 90)), ((30, 34, 70), (10, 12, 30)),
]

INTRO_D, SCENE_D, MOMENT_D, SUMMARY_D, END_D = 13.0, 19.0, 20.0, 40.0, 13.0

ITEM_T = [1.4, 2.9, 4.4]
PQ_T, RQ_T, CAP_T = 6.4, 9.6, 13.6
CPS = 9.0  # typewriter characters per second

MOMENTS = [
    "学会走路时，都跌跌撞撞扑进了妈妈怀里",
    "第一次心动时，都偷偷写过一页日记",
    "第一次被生活打倒时，都在深夜哭过",
    "送走父母的那天，都哭得像个孩子",
]
MOMENT_T = [3.0, 6.0, 9.0, 12.0]

CARDS = [
    ("起点的差距，是真实的。", "教育、眼界、试错的机会，确实不一样。"),
    ("但幸福，不按价格分配。", "陪伴、理解和爱，每个家庭都给得起。"),
    ("普通不等于失败，富裕也不等于轻松。", "每个人都在自己的路上，负重前行。"),
    ("我们无法选择出身，", "但可以选择成为怎样的人，给下一代怎样的起点。"),
]
CARD_T = [3.0, 11.0, 19.0, 27.0]


def build_timeline():
    segs, t = [], 0.0
    segs.append(("intro", t, INTRO_D, None)); t += INTRO_D
    for i in range(len(SCENES)):
        segs.append(("scene", t, SCENE_D, i)); t += SCENE_D
    segs.append(("moment", t, MOMENT_D, None)); t += MOMENT_D
    segs.append(("summary", t, SUMMARY_D, None)); t += SUMMARY_D
    segs.append(("end", t, END_D, None)); t += END_D
    return segs, t


SEGS, TOTAL = build_timeline()


def ease(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def mix(c, bg, a):
    return tuple(int(bg[i] + (c[i] - bg[i]) * a) for i in range(3))


def vgrad(w, h, top, bottom):
    t = np.linspace(0, 1, h)[:, None, None]
    arr = (np.array(top) * (1 - t) + np.array(bottom) * t).astype(np.uint8)
    return Image.fromarray(np.repeat(arr, w, axis=1), "RGB")


def radial_bg(center_col, edge_col):
    y, x = np.mgrid[0:H, 0:W]
    r = np.sqrt(((x - W / 2) / (W * 0.6)) ** 2 + ((y - H * 0.45) / (H * 0.7)) ** 2)
    r = np.clip(r, 0, 1)[..., None]
    arr = np.array(center_col) * (1 - r) + np.array(edge_col) * r
    return Image.fromarray(arr.astype(np.uint8), "RGB")


def ctext(d, x, y, s, f, fill):
    d.text((x - d.textlength(s, font=f) / 2, y), s, font=f, fill=fill)


def wrap(d, s, f, maxw):
    lines, cur = [], ""
    for ch in s:
        if d.textlength(cur + ch, font=f) > maxw and cur and ch not in "”。，！？、":
            lines.append(cur)
            cur = ch
        else:
            cur += ch
    if cur:
        lines.append(cur)
    return lines


# ---------- illustration (drawn at 2x then downsampled for anti-aliasing) ----------

def draw_person(d, cx, base, age, color, k):
    if age == 0:
        d.rounded_rectangle((cx - 70 * k, base - 56 * k, cx + 70 * k, base), 26 * k, fill=(230, 230, 236))
        d.rounded_rectangle((cx - 70 * k, base - 56 * k, cx + 70 * k, base - 44 * k), 8 * k, fill=color)
        d.ellipse((cx - 22 * k, base - 104 * k, cx + 22 * k, base - 60 * k), fill=(246, 214, 186))
        d.ellipse((cx - 44 * k, base - 72 * k, cx + 44 * k, base - 30 * k), fill=color)
        return
    s = min(1.0, 0.42 + age / 18 * 0.58)
    h = 200 * s * k
    stoop = 8 * k if age >= 60 else 0
    head_r = (22 * s + 8) * k
    top = base - h
    hx = cx + stoop
    skin = (246, 214, 186)
    hair = (220, 220, 225) if age >= 60 else ((140, 140, 150) if age >= 42 else (50, 40, 36))
    d.ellipse((hx - head_r, top, hx + head_r, top + 2 * head_r), fill=skin)
    d.chord((hx - head_r, top - 2 * k, hx + head_r, top + 1.3 * head_r), 180, 360, fill=hair)
    bt = top + 2 * head_r + 3 * k
    bb = base - h * 0.4
    bw = (18 * s + 8) * k
    d.rounded_rectangle((cx - bw, bt, cx + bw, bb), 14 * k, fill=color)
    lw = int(max(6, 10 * s) * k)
    leg = tuple(max(0, c - 50) for c in color)
    d.line((cx - bw * 0.45, bb - 4 * k, cx - bw * 0.55, base), fill=leg, width=lw)
    d.line((cx + bw * 0.45, bb - 4 * k, cx + bw * 0.55, base), fill=leg, width=lw)
    d.line((cx - bw, bt + 10 * k, cx - bw - 14 * s * k, bt + 70 * s * k), fill=color, width=lw)
    d.line((cx + bw, bt + 10 * k, cx + bw + 14 * s * k, bt + 70 * s * k), fill=color, width=lw)
    if age >= 60:
        d.line((cx + bw + 14 * s * k, bt + 70 * s * k, cx + bw + 26 * k, base), fill=(150, 110, 70), width=6 * k)


def skyline(d, x0, y_base, x1, rng, hmin, hmax, wmin, wmax, col, lit, k):
    x = x0
    while x < x1:
        w = rng.integers(wmin, wmax) * k
        h = rng.integers(hmin, hmax) * k
        d.rectangle((x, y_base - h, x + w, y_base), fill=col)
        if lit:
            for wy in range(int(y_base - h + 8 * k), int(y_base - 6 * k), int(14 * k)):
                for wx in range(int(x + 5 * k), int(x + w - 6 * k), int(11 * k)):
                    if rng.random() < 0.35:
                        d.rectangle((wx, wy, wx + 4 * k, wy + 6 * k), fill=(255, 220, 140))
        x += w + rng.integers(2, 8) * k


def banner(idx, rich, bw, bh):
    k = 2
    age = SCENES[idx][0]
    desk = SCENES[idx][10]
    sky_top, sky_bot = SKY[idx]
    night = idx >= 8
    w, h = bw * k, bh * k
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    wall = (58, 52, 50) if not rich else (70, 64, 58)
    d.rectangle((0, 0, w, h), fill=wall)
    floor_y = int(h * 0.82)
    floor = (92, 70, 56) if not rich else (200, 192, 178)
    d.rectangle((0, floor_y, w, h), fill=floor)
    rng = np.random.default_rng(idx * 7 + (1 if rich else 0))
    if rich:
        wx0, wy0, wx1, wy1 = int(w * 0.32), int(h * 0.06), int(w * 0.97), floor_y
    else:
        wx0, wy0, wx1, wy1 = int(w * 0.45), int(h * 0.16), int(w * 0.80), int(h * 0.60)
    sky = vgrad(wx1 - wx0, wy1 - wy0, sky_top, sky_bot)
    img.paste(sky, (wx0, wy0))
    if night:
        for _ in range(40):
            sx, sy = rng.integers(wx0, wx1), rng.integers(wy0, wy0 + (wy1 - wy0) // 2)
            d.ellipse((sx, sy, sx + 3 * k, sy + 3 * k), fill=(240, 240, 255))
    sil = tuple(int(c * 0.45) for c in sky_bot)
    if rich:
        d.rectangle((wx0, wy1 - 70 * k, wx1, wy1), fill=tuple(int(c * 0.7) for c in sky_bot))
        skyline(d, wx0, wy1 - 70 * k, wx1, rng, 60, 200, 18, 40, sil, night or idx >= 6, k)
        for fx in np.linspace(wx0, wx1, 5):
            d.rectangle((fx - 3 * k, wy0, fx + 3 * k, wy1), fill=(40, 38, 40))
    else:
        skyline(d, wx0, wy1, wx1, rng, 40, 120, 30, 60, sil, night or idx >= 6, k)
        d.rectangle((wx0, wy0, wx1, wy1), outline=(120, 100, 80), width=8 * k)
        mid = (wx0 + wx1) // 2
        d.line((mid, wy0, mid, wy1), fill=(120, 100, 80), width=6 * k)
        d.rectangle((wx0 - 10 * k, wy1, wx1 + 10 * k, wy1 + 10 * k), fill=(110, 90, 72))
    if desk:
        dx = int(w * 0.62) if not rich else int(w * 0.55)
        dcol = (120, 86, 60) if not rich else (60, 50, 46)
        d.rectangle((dx, floor_y - 70 * k, dx + 190 * k, floor_y - 58 * k), fill=dcol)
        d.rectangle((dx + 10 * k, floor_y - 58 * k, dx + 20 * k, floor_y), fill=dcol)
        d.rectangle((dx + 170 * k, floor_y - 58 * k, dx + 180 * k, floor_y), fill=dcol)
        for j in range(4):
            d.rectangle((dx + 24 * k + j * 6 * k, floor_y - 70 * k - (14 + j * 7) * k,
                         dx + 90 * k + j * 3 * k, floor_y - 70 * k - j * 7 * k),
                        fill=[(200, 80, 70), (80, 140, 200), (230, 200, 90), (120, 180, 120)][j])
        d.line((dx + 150 * k, floor_y - 70 * k, dx + 150 * k, floor_y - 130 * k), fill=(200, 200, 200), width=4 * k)
        d.polygon([(dx + 130 * k, floor_y - 120 * k), (dx + 170 * k, floor_y - 120 * k), (dx + 160 * k, floor_y - 140 * k), (dx + 140 * k, floor_y - 140 * k)], fill=(255, 220, 140))
    if rich and not desk:
        d.rounded_rectangle((int(w * 0.7), floor_y - 60 * k, int(w * 0.95), floor_y), 16 * k, fill=(150, 120, 90))
        d.rounded_rectangle((int(w * 0.7), floor_y - 90 * k, int(w * 0.95), floor_y - 50 * k), 16 * k, fill=(170, 140, 110))
    if not rich and not desk:
        d.rectangle((int(w * 0.84), floor_y - 110 * k, int(w * 0.95), floor_y), fill=(100, 80, 64))
        d.rectangle((int(w * 0.85), floor_y - 100 * k, int(w * 0.94), floor_y - 58 * k), fill=(80, 64, 52))
    light = Image.new("L", (w, h), 0)
    ImageDraw.Draw(light).ellipse((wx0 - 200 * k, wy0, wx1 + 100 * k, h + 200 * k), fill=50)
    light = light.filter(ImageFilter.GaussianBlur(60 * k))
    img = Image.composite(Image.new("RGB", (w, h), sky_top), img, light)
    d = ImageDraw.Draw(img)
    color = RICH if rich else POOR
    pcx = int(w * 0.2)
    shadow = Image.new("L", (w, h), 0)
    ImageDraw.Draw(shadow).ellipse((pcx - 80 * k, floor_y + 18 * k, pcx + 80 * k, floor_y + 40 * k), fill=90)
    shadow = shadow.filter(ImageFilter.GaussianBlur(8 * k))
    img = Image.composite(Image.new("RGB", (w, h), (0, 0, 0)), img, shadow)
    d = ImageDraw.Draw(img)
    draw_person(d, pcx, floor_y + 30 * k, age, color, k)
    vign = vgrad(w, h, (0, 0, 0), (0, 0, 0))
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rectangle((0, 0, w, h), outline=110, width=40 * k)
    mask = mask.filter(ImageFilter.GaussianBlur(30 * k))
    img = Image.composite(vign, img, mask)
    img = img.resize((bw, bh), Image.LANCZOS)
    rmask = Image.new("L", (bw, bh), 0)
    ImageDraw.Draw(rmask).rounded_rectangle((0, 0, bw - 1, bh - 1), 18, fill=255)
    return img, rmask


PX = [60, 990]
PW = 870
PANEL_Y = (130, 900)
BANNER = (20, 70, 830, 300)  # x, y offset within panel, w, h

_cache = {}


def scene_base(idx):
    if idx in _cache:
        return _cache[idx]
    img = vgrad(W, H, (20, 23, 36), BG)
    d = ImageDraw.Draw(img)
    for side in range(2):
        x0 = PX[side]
        color = RICH if side else POOR
        d.rounded_rectangle((x0, PANEL_Y[0], x0 + PW, PANEL_Y[1]), 28, fill=PANEL, outline=tuple(int(c * 0.55) for c in color), width=2)
        b, m = banner(idx, side == 1, BANNER[2], BANNER[3])
        img.paste(b, (x0 + BANNER[0], PANEL_Y[0] + BANNER[1]), m)
    _cache[idx] = img
    return img


def typed(s, lt, start):
    n = int(max(0.0, lt - start) * CPS)
    return s[:n], n < len(s)


def draw_scene(idx, lt):
    age, stage, pitems, ritems, pq, rq, cap, ptag, rtag = SCENES[idx][:9]
    base = scene_base(idx)
    img = base.copy()
    d = ImageDraw.Draw(img)
    prog = (idx + lt / SCENE_D) / len(SCENES)
    d.rectangle((0, 0, W, 6), fill=(36, 40, 58))
    d.rectangle((0, 0, int(W * prog), 6), fill=(150, 170, 240))
    age_s = "出生" if age == 0 else f"{age} 岁"
    hp = ease(lt / 0.8)
    ctext(d, W / 2, 34, f"{age_s} · {stage}" if age else "0 岁 · 出生", F["age"], mix(TEXT, BG, hp))
    for side in range(2):
        x0 = PX[side]
        color = RICH if side else POOR
        title = "富裕家庭的孩子" if side else "普通家庭的孩子"
        items = ritems if side else pitems
        quote = rq if side else pq
        tag = rtag if side else ptag
        d.text((x0 + 28, PANEL_Y[0] + 16), title, font=F["head"], fill=color)
        tp = ease((lt - 0.8) / 0.6)
        if tp > 0:
            tw = d.textlength(tag, font=F["tag"]) + 36
            tx = x0 + PW - 28 - tw
            ty = PANEL_Y[0] + 20
            d.rounded_rectangle((tx, ty, tx + tw, ty + 42), 21, fill=mix(color, PANEL, 0.25 * tp), outline=mix(color, PANEL, tp), width=2)
            d.text((tx + 18, ty + 4), tag, font=F["tag"], fill=mix(color, PANEL, tp))
        iy = PANEL_Y[0] + BANNER[1] + BANNER[3] + 30
        for i, s in enumerate(items):
            p = ease((lt - ITEM_T[i]) / 0.7)
            if p <= 0:
                continue
            y = iy + i * 58
            tx = x0 + 60 + (1 - p) * 40
            d.ellipse((tx - 26, y + 14, tx - 14, y + 26), fill=mix(color, PANEL, p))
            d.text((tx, y), s, font=F["item"], fill=mix(TEXT, PANEL, p))
        qs = RQ_T if side else PQ_T
        if lt >= qs - 0.4:
            qy = iy + 3 * 58 + 22
            qp = ease((lt - qs + 0.4) / 0.4)
            d.rounded_rectangle((x0 + 28, qy, x0 + PW - 28, PANEL_Y[1] - 24), 18, fill=mix((34, 38, 56), PANEL, qp))
            d.rectangle((x0 + 28, qy + 14, x0 + 34, PANEL_Y[1] - 38), fill=mix(color, PANEL, qp))
            shown, typing = typed(quote, lt, qs)
            lines = wrap(d, "“" + quote + "”", F["quote"], PW - 120)
            remaining = len(shown) + 1 + (0 if typing else 1)
            for li, line in enumerate(lines):
                part = line[:max(0, remaining)]
                remaining -= len(line)
                if part:
                    d.text((x0 + 60, qy + 22 + li * 46), part, font=F["quote"], fill=WARM)
    cp = ease((lt - CAP_T) / 0.9)
    if cp > 0:
        bg = BG
        d.rounded_rectangle((200, 930, W - 200, 1030), 26, fill=mix((30, 33, 50), bg, cp))
        ctext(d, W / 2, 955, cap, F["cap"], mix(WARM, bg, cp))
    return img


INTRO_BG = None
MOMENT_BG = None


def draw_intro(lt):
    global INTRO_BG
    if INTRO_BG is None:
        INTRO_BG = radial_bg((34, 30, 56), (6, 6, 12))
    img = INTRO_BG.copy()
    d = ImageDraw.Draw(img)
    bg = (24, 22, 40)
    beat = (math.sin(lt * 2 * math.pi) * 0.5 + 0.5) ** 6
    for side, col in enumerate([POOR, RICH]):
        p = ease((lt - 1.0 - side * 0.6) / 1.5)
        if p <= 0:
            continue
        cx = W / 2 + (-1 if side == 0 else 1) * (40 + 260 * ease((lt - 5.5) / 2.0))
        r = 14 + 6 * beat
        glow = 60 + 20 * beat
        d.ellipse((cx - glow, 330 - glow, cx + glow, 330 + glow), fill=mix(col, bg, 0.12 * p))
        d.ellipse((cx - r, 330 - r, cx + r, 330 + r), fill=mix(col, bg, p))
    l1 = ease((lt - 2.5) / 1.2)
    ctext(d, W / 2, 470, "同一天，两个孩子出生了。", F["sub"], mix(TEXT, bg, l1))
    l2 = ease((lt - 6.0) / 1.2)
    ctext(d, W / 2, 560, "两个孩子的一生", F["hero"], mix((255, 255, 255), bg, l2))
    l3 = ease((lt - 8.0) / 1.2)
    ctext(d, W / 2, 700, "普通家庭  ×  富裕家庭", F["sub"], mix((190, 196, 225), bg, l3))
    return img


def draw_moment(lt):
    global MOMENT_BG
    if MOMENT_BG is None:
        MOMENT_BG = radial_bg((48, 36, 34), (8, 7, 10))
    img = MOMENT_BG.copy()
    d = ImageDraw.Draw(img)
    bg = (34, 26, 26)
    p = ease(lt / 1.2)
    ctext(d, W / 2, 150, "可是，他们也有一模一样的时刻", F["title"], mix(WARM, bg, p))
    for i, s in enumerate(MOMENTS):
        q = ease((lt - MOMENT_T[i]) / 1.0)
        if q > 0:
            y = 330 + i * 110 + (1 - q) * 20
            ctext(d, W / 2, y, s, F["sub"], mix(TEXT, bg, q))
            d.ellipse((W / 2 - 520, y + 18, W / 2 - 506, y + 32), fill=mix(POOR, bg, q))
            d.ellipse((W / 2 + 506, y + 18, W / 2 + 520, y + 32), fill=mix(RICH, bg, q))
    c = ease((lt - 15.5) / 1.2)
    ctext(d, W / 2, 860, "有些东西，钱买不到，也换不走。", F["cap"], mix((255, 210, 160), bg, c))
    return img


def draw_summary(lt):
    img = vgrad(W, H, (18, 20, 34), (8, 8, 14))
    d = ImageDraw.Draw(img)
    bg = (14, 15, 25)
    p = ease(lt / 1.2)
    ctext(d, W / 2, 80, "写在最后", F["title"], mix(WARM, bg, p))
    d.rectangle((W / 2 - 60, 170, W / 2 + 60, 174), fill=mix(WARM, bg, p))
    for i, (h1, h2) in enumerate(CARDS):
        q = ease((lt - CARD_T[i]) / 1.2)
        if q <= 0:
            continue
        y = 230 + i * 190 + (1 - q) * 30
        cbg = mix((30, 33, 52), bg, q)
        d.rounded_rectangle((260, y, W - 260, y + 160), 24, fill=cbg)
        accent = [POOR, RICH, (170, 140, 220), (240, 160, 120)][i]
        d.rounded_rectangle((260, y, 272, y + 160), 6, fill=mix(accent, bg, q))
        d.text((320, y + 26), h1, font=F["card"], fill=mix((255, 255, 255), bg, q))
        d.text((320, y + 96), h2, font=F["cardsub"], fill=mix((190, 196, 220), bg, q))
    return img


def draw_end(lt):
    img = Image.new("RGB", (W, H), (6, 6, 10))
    d = ImageDraw.Draw(img)
    bg = (6, 6, 10)
    l1 = ease((lt - 0.8) / 1.5)
    ctext(d, W / 2, 400, "愿每一个孩子，都被认真爱过。", F["title"], mix((255, 255, 255), bg, l1))
    l2 = ease((lt - 3.5) / 1.5)
    ctext(d, W / 2, 530, "—— 献给每一位努力生活的父母", F["sub"], mix((180, 180, 200), bg, l2))
    return img


def frame_at(t):
    for kind, start, dur, idx in SEGS:
        if t < start + dur:
            lt = t - start
            img = {"intro": draw_intro, "moment": draw_moment, "summary": draw_summary, "end": draw_end}.get(kind)
            img = draw_scene(idx, lt) if kind == "scene" else img(lt)
            fin = 0.6 if kind != "end" else 1.2
            fout = 0.7 if kind != "end" else 3.0
            a = min(ease(lt / fin), ease((dur - lt) / fout))
            if a < 1:
                img = Image.blend(Image.new("RGB", (W, H)), img, a)
            return img
    return Image.new("RGB", (W, H))


# ---------- audio ----------

def lowpass(x, cutoff):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X *= 1 / (1 + (f / cutoff) ** 4)
    return np.fft.irfft(X, len(x))


def bandpass(x, lo, hi):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X *= (1 / (1 + (lo / np.maximum(f, 1)) ** 4)) * (1 / (1 + (f / hi) ** 4))
    return np.fft.irfft(X, len(x))


def reverb(x, secs=2.4, wet=0.35, seed=0):
    rng = np.random.default_rng(seed)
    n = int(secs * SR)
    ir = rng.standard_normal(n) * np.exp(-np.arange(n) / SR * 3.2)
    ir = lowpass(ir, 5000)
    ir /= np.sqrt(np.sum(ir ** 2))
    L = 1 << int(np.ceil(np.log2(len(x) + n)))
    y = np.fft.irfft(np.fft.rfft(x, L) * np.fft.rfft(ir, L), L)[:len(x)]
    return x * (1 - wet) + y * wet * 3


def piano(freq, dur, vel=1.0):
    t = np.arange(int(dur * SR)) / SR
    out = np.zeros_like(t)
    for h in range(1, 8):
        amp = vel / h ** 1.6
        out += amp * np.exp(-t * (1.2 + h * 0.9)) * np.sin(2 * np.pi * freq * h * (1 + 0.0004 * h * h) * t)
    out *= np.minimum(1, t * 300)
    return out


def note(name):
    names = {"C": 0, "C#": 1, "D": 2, "Eb": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "Ab": 8, "A": 9, "Bb": 10, "B": 11}
    pitch, octv = name[:-1], int(name[-1])
    return 440 * 2 ** ((names[pitch] + 12 * (octv + 1) - 69) / 12)


def place(buf, sig, t, gain=1.0, pan=0.0):
    s = int(t * SR)
    if s >= buf.shape[1]:
        return
    e = min(buf.shape[1], s + len(sig))
    l, r = math.cos((pan + 1) * math.pi / 4), math.sin((pan + 1) * math.pi / 4)
    buf[0, s:e] += sig[:e - s] * gain * l * 1.41
    buf[1, s:e] += sig[:e - s] * gain * r * 1.41


def sfx_pop(f0=880):
    t = np.arange(int(0.18 * SR)) / SR
    f = f0 * (1 - 0.3 * t / 0.18)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 28)


def sfx_click(rng):
    n = int(0.012 * SR)
    x = rng.standard_normal(n) * np.exp(-np.arange(n) / SR * 600)
    return bandpass(np.pad(x, (0, 400)), 1500, 7000)


def sfx_whoosh(rng, dur=1.1):
    n = int(dur * SR)
    x = rng.standard_normal(n)
    out = np.zeros(n)
    for i, (lo, hi) in enumerate([(200, 800), (500, 1600), (1000, 3000)]):
        seg = bandpass(x, lo, hi)
        env = np.sin(np.linspace(0, np.pi, n)) ** (2 + i)
        out += seg * env
    return out / np.max(np.abs(out))


def sfx_chime():
    t = np.arange(int(3.0 * SR)) / SR
    out = sum(a * np.sin(2 * np.pi * 1318.5 * r * t) * np.exp(-t * d)
              for r, a, d in [(1, 1, 1.6), (2.76, 0.4, 3), (5.4, 0.2, 5)])
    return out * np.minimum(1, t * 500)


def sfx_heart():
    t = np.arange(int(0.9 * SR)) / SR
    def thump(t0, g):
        tt = np.maximum(0, t - t0)
        return g * np.sin(2 * np.pi * 55 * tt) * np.exp(-tt * 18) * (t >= t0)
    return thump(0, 1.0) + thump(0.22, 0.7)


def sfx_bell():
    out = np.zeros(int(2.6 * SR))
    for i in range(3):
        for j, f in enumerate([1046.5, 1318.5, 1568.0]):
            s = piano(f, 1.6, 0.6)
            st = int((i * 0.7 + j * 0.18) * SR)
            out[st:st + len(s)] += s[:len(out) - st]
    return out


def sfx_tick(hi):
    n = int(0.03 * SR)
    t = np.arange(n) / SR
    return np.sin(2 * np.pi * (2400 if hi else 1800) * t) * np.exp(-t * 250)


def ambience_noise(rng, dur, lo, hi):
    n = int(dur * SR)
    x = bandpass(rng.standard_normal(n), lo, hi)
    x /= np.max(np.abs(x))
    env = np.minimum(1, np.minimum(np.arange(n), n - np.arange(n)) / (1.5 * SR))
    return x * env


def sfx_train(rng, dur):
    n = int(dur * SR)
    base = ambience_noise(rng, dur, 60, 400) * 0.6
    t = np.arange(n) / SR
    for i in range(int(dur / 0.9)):
        for off in (0, 0.14):
            tt = t - (i * 0.9 + off)
            m = (tt >= 0) & (tt < 0.15)
            base[m] += 0.5 * np.sin(2 * np.pi * 90 * tt[m]) * np.exp(-tt[m] * 30)
    return base


def make_music():
    n = int(TOTAL * SR) + SR
    mus = np.zeros(n)
    bpm = 66
    beat = 60 / bpm
    prog = [("A2", ["A3", "C4", "E4", "C4", "A4", "E4", "C4", "E4"]),
            ("F2", ["F3", "A3", "C4", "A3", "F4", "C4", "A3", "C4"]),
            ("C3", ["C4", "E4", "G4", "E4", "C5", "G4", "E4", "G4"]),
            ("G2", ["G3", "B3", "D4", "B3", "G4", "D4", "B3", "D4"])]
    melody = ["E5", None, "D5", "C5", None, None, "A4", None, "C5", None, "B4", "A4", None, None, "G4", None,
              "E5", None, "G5", "E5", None, "D5", "C5", None, "D5", None, "B4", "G4", None, None, None, None]
    start = 3.0
    moment_start = [s for k, s, _, _ in SEGS if k == "moment"][0]
    bar = 0
    t = start
    while t < TOTAL - 6:
        bass, arp = prog[bar % 4]
        mus_s = int(t * SR)
        sig = piano(note(bass), 4 * beat + 2, 0.55) + piano(note(bass) * 2, 4 * beat + 2, 0.25)
        mus[mus_s:mus_s + len(sig)] += sig[:n - mus_s]
        for j, nm in enumerate(arp):
            st = t + j * beat / 2
            s = piano(note(nm), 2.5, 0.32 if j % 2 == 0 else 0.24)
            si = int(st * SR)
            mus[si:si + len(s)] += s[:n - si]
        if t >= moment_start - 1:
            for j in range(8):
                nm = melody[(bar % 4) * 8 + j]
                if nm:
                    st = t + j * beat / 2
                    s = piano(note(nm), 3.0, 0.5)
                    si = int(st * SR)
                    mus[si:si + len(s)] += s[:n - si]
        bar += 1
        t += 4 * beat
    tt = np.arange(n) / SR
    pad = np.zeros(n)
    m = tt >= moment_start - 2
    for f in [220, 261.6, 329.6]:
        pad[m] += np.sin(2 * np.pi * f * tt[m]) * 0.05
    pad = lowpass(pad, 900) * np.clip((tt - moment_start + 2) / 6, 0, 1)
    mus = reverb(mus + pad, 2.8, 0.4, seed=1)
    fade_in = np.clip((tt - start) / 2, 0, 1)
    fade_out = np.clip((TOTAL - tt) / 8, 0, 1)
    return mus * fade_in * fade_out


def make_audio(path):
    rng = np.random.default_rng(42)
    n = int(TOTAL * SR) + SR
    buf = np.zeros((2, n))
    mus = make_music()
    mus = mus / np.max(np.abs(mus)) * 0.38
    buf += mus
    sfx = np.zeros((2, n))
    for i in range(10):
        place(sfx, sfx_heart(), 0.4 + i * 1.0, 0.55 * (1 - i / 12))
    pop, click, whoosh, chime = sfx_pop(), None, sfx_whoosh(rng), sfx_chime()
    for kind, start, dur, idx in SEGS:
        if kind != "intro":
            place(sfx, whoosh, start - 0.55, 0.16)
        if kind == "scene":
            sc = SCENES[idx]
            for side, pan in ((0, -0.6), (1, 0.6)):
                for it in ITEM_T:
                    place(sfx, sfx_pop(760 if side == 0 else 1020), start + it + side * 0.12, 0.10, pan)
                qs = RQ_T if side else PQ_T
                q = sc[5] if side else sc[4]
                for c in range(len(q)):
                    place(sfx, sfx_click(rng), start + qs + c / CPS, 0.09 * rng.uniform(0.6, 1.0), pan)
            place(sfx, chime, start + CAP_T, 0.07)
            amb = sc[9]
            if amb == "heart":
                for b in range(6):
                    place(sfx, sfx_heart(), start + 0.5 + b * 0.85, 0.35)
            elif amb == "bell":
                place(sfx, sfx_bell(), start + 0.3, 0.12)
            elif amb == "clock":
                for b in range(int(dur)):
                    place(sfx, sfx_tick(b % 2 == 0), start + b + 0.2, 0.10)
            elif amb == "rain":
                place(sfx, ambience_noise(rng, dur, 1500, 9000), start, 0.05, -0.1)
                place(sfx, ambience_noise(rng, dur, 1500, 9000), start, 0.05, 0.1)
            elif amb == "train":
                place(sfx, sfx_train(rng, 8), start, 0.18)
            elif amb == "subway":
                place(sfx, ambience_noise(rng, dur, 80, 600), start, 0.10)
        elif kind == "moment":
            for mt in MOMENT_T:
                place(sfx, chime, start + mt, 0.05)
        elif kind == "summary":
            for ct in CARD_T:
                place(sfx, sfx_pop(520), start + ct, 0.12)
        elif kind == "end":
            for b in range(5):
                place(sfx, sfx_heart(), start + 4 + b * 1.1, 0.35 * (1 - b / 5))
    buf += sfx
    buf /= max(1.0, np.max(np.abs(buf)) / 0.95)
    data = (buf.T * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())


# ---------- render ----------

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
    n_chunks = 12
    step = math.ceil(frames / n_chunks)
    jobs = [(i, i * step, min(frames, (i + 1) * step)) for i in range(n_chunks)]
    with Pool(int(sys.argv[1]) if len(sys.argv) > 1 else os.cpu_count()) as pool:
        audio = pool.apply_async(make_audio, (f"{TMP}/audio.wav",))
        chunks = pool.map(render_chunk, jobs)
        audio.get()
    with open(f"{TMP}/list.txt", "w") as f:
        f.writelines(f"file '{c}'\n" for c in chunks)
    out = f"{OUT_DIR}/two_lives.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", f"{TMP}/list.txt",
        "-i", f"{TMP}/audio.wav", "-c:v", "copy", "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
        "-ar", "44100", "-c:a", "aac", "-b:a", "192k",
        "-shortest", "-movflags", "+faststart", out,
    ], check=True)
    print(out, f"{TOTAL:.1f}s")


if __name__ == "__main__":
    main()
