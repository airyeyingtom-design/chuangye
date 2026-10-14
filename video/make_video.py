import math
import subprocess
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1280, 720, 24
FONT = "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"
OUT_DIR = "/workspace/video"


def font(size):
    return ImageFont.truetype(FONT, size)


F_TITLE, F_SUB, F_AGE, F_HEAD, F_ITEM, F_CAP, F_SMALL = (
    font(64), font(30), font(44), font(32), font(26), font(28), font(20))

POOR = (86, 140, 200)
RICH = (214, 170, 70)

SCENES = [
    ("0 岁 · 出生", 1,
     ["公立医院多人病房", "爸妈请假轮流照顾", "奶粉尿布精打细算"],
     ["私立医院 VIP 产房", "月嫂 + 育儿嫂 24 小时", "进口奶粉，早教已规划"],
     "起点不同，但爸妈的爱一样多。", 2, 9),
    ("3 岁 · 幼儿园", 3,
     ["爷爷奶奶帮忙带大", "小区滑梯就是乐园", "就近上普惠幼儿园"],
     ["双语国际幼儿园", "钢琴、马术、外教", "周末常去海外度假"],
     "孩子最早的世界，是家里给的。", 4, 22),
    ("7 岁 · 小学", 7,
     ["就近入学公立小学", "放学后自己写作业", "兴趣班要咬牙报一个"],
     ["名校学区房 / 国际学校", "一对一私教辅导", "夏令营遍布全球"],
     "差距开始从“选择有多少”体现出来。", 6, 35),
    ("13 岁 · 初中", 13,
     ["拼成绩，拼中考", "父母加班，自己热饭", "用的是旧款手机"],
     ["升学路径早有规划", "竞赛、科研项目背景", "眼界来自世界各地"],
     "一个在学习生存，一个在学习选择。", 9, 48),
    ("16 岁 · 高中", 16,
     ["高考，是改变命运的路", "题海战术，熬夜刷题", "志愿看分数和就业"],
     ["备考 SAT / A-Level", "留学顾问全程规划", "专业看兴趣和名校"],
     "同样是十六岁，压力的形状不同。", 12, 60),
    ("18 岁 · 大学", 19,
     ["国内大学，兼职赚生活费", "每顿饭都会算一算", "自己摸索找实习"],
     ["海外名校，无经济压力", "专心探索自己的兴趣", "家人引荐顶级实习"],
     "一个在独立中成长，一个在探索中成长。", 16, 70),
    ("23 岁 · 初入职场", 23,
     ["海投简历，从基层做起", "合租房，通勤一小时", "每月想着存一点钱"],
     ["进入家族企业或顶级机构", "住在市中心", "父母提供创业启动资金"],
     "试错的成本，决定了敢不敢冒险。", 22, 78),
    ("28 岁 · 成家", 28,
     ["全家凑首付", "背上三十年房贷", "婚礼简单而温馨"],
     ["全款买房", "资产配置、婚前规划", "婚礼盛大而隆重"],
     "家，对一个是目标，对另一个是起点。", 28, 85),
    ("40 岁 · 中年", 40,
     ["上有老，下有小", "担心裁员、房贷、学费", "拼命给孩子更好的起点"],
     ["打理资产与事业", "关注健康与家族传承", "财富在复利中增长"],
     "普通人最大的愿望：让下一代少走弯路。", 38, 92),
    ("65 岁 · 晚年", 65,
     ["退休金 + 一辈子的积蓄", "帮忙带孙辈", "简单生活，知足常乐"],
     ["高端医疗与养老服务", "家族信托规划传承", "带着老伴环球旅行"],
     "走到最后，健康和陪伴最珍贵。", 45, 96),
    ("回望一生", 70,
     ["“这一路，我靠自己走到了这里”", "收获：韧性、独立、懂得珍惜", ""],
     ["“我拥有更多的选择”", "收获：视野、资源、机会", ""],
     "两种人生，各有各的压力，也各有各的幸福。", 50, 100),
]

TITLE_DUR, SCENE_DUR, END_DUR = 9.0, 15.0, 12.0
TOTAL = TITLE_DUR + SCENE_DUR * len(SCENES) + END_DUR


def ease(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def gradient(top, bottom):
    t = np.linspace(0, 1, H)[:, None, None]
    arr = (np.array(top) * (1 - t) + np.array(bottom) * t).astype(np.uint8)
    return Image.fromarray(np.repeat(arr, W, axis=1), "RGB")


BG_SCENE = gradient((22, 26, 40), (12, 14, 22))
BG_TITLE = gradient((30, 24, 50), (10, 10, 18))


def ctext(d, x, y, s, f, fill):
    w = d.textlength(s, font=f)
    d.text((x - w / 2, y), s, font=f, fill=fill)


def fade(c, a, bg=(16, 18, 28)):
    return tuple(int(bg[i] + (c[i] - bg[i]) * a) for i in range(3))


def person(d, cx, base, age, color, rich, t, a):
    """Simple figure whose height grows with age; elderly figures stoop slightly."""
    if age <= 1:
        s = 0.35
    elif age < 18:
        s = 0.45 + age / 18 * 0.55
    else:
        s = 1.0
    stoop = 6 if age >= 65 else 0
    bob = math.sin(t * 2.4) * 2
    col = fade(color, a)
    skin = fade((240, 210, 180), a)
    h = 150 * s
    head_r = 18 * s + 6
    top = base - h + bob
    hx = cx + stoop
    if age <= 1:
        d.rounded_rectangle((cx - 45, base - 40, cx + 45, base), 18, fill=fade((70, 80, 100), a))
        d.ellipse((cx - 14, base - 66, cx + 14, base - 38), fill=skin)
        d.ellipse((cx - 30, base - 44, cx + 30, base - 16), fill=col)
        return
    d.ellipse((hx - head_r, top, hx + head_r, top + 2 * head_r), fill=skin)
    if age >= 65:
        d.arc((hx - head_r, top - 2, hx + head_r, top + 2 * head_r), 200, 340, fill=fade((220, 220, 220), a), width=5)
    body_top = top + 2 * head_r + 2
    body_bot = base - h * 0.38
    d.rounded_rectangle((cx - 16 * s - 6, body_top, cx + 16 * s + 6, body_bot), 10, fill=col)
    lw = max(4, int(7 * s))
    d.line((cx - 7 * s, body_bot, cx - 10 * s, base), fill=col, width=lw)
    d.line((cx + 7 * s, body_bot, cx + 10 * s, base), fill=col, width=lw)
    swing = math.sin(t * 3) * 6
    d.line((cx - 16 * s - 6, body_top + 8, cx - 30 * s - 6, body_top + 45 * s + swing), fill=col, width=lw)
    d.line((cx + 16 * s + 6, body_top + 8, cx + 30 * s + 6, body_top + 45 * s - swing), fill=col, width=lw)
    if age >= 65:
        d.line((cx + 30 * s + 6, body_top + 45 * s, cx + 36 * s + 10, base), fill=fade((150, 110, 70), a), width=4)
    if rich:
        gold = fade((255, 215, 90), a)
        d.polygon([(hx - 10, top + 4), (hx - 6, top - 10), (hx, top + 0), (hx + 6, top - 10), (hx + 10, top + 4)], fill=gold)


def draw_scene(idx, lt, gt):
    age_label, age, poor, rich, cap, poor_res, rich_res = SCENES[idx]
    a = ease(lt / 0.8) * (1 - ease((lt - (SCENE_DUR - 0.8)) / 0.8))
    img = BG_SCENE.copy()
    d = ImageDraw.Draw(img)

    d.rectangle((0, 0, W, 6), fill=(40, 44, 60))
    prog = (idx + lt / SCENE_DUR) / len(SCENES)
    d.rectangle((0, 0, int(W * prog), 6), fill=(140, 160, 230))

    ctext(d, W / 2, 26, age_label, F_AGE, fade((240, 240, 250), a))
    d.line((W / 2, 100, W / 2, 560), fill=fade((60, 64, 84), a), width=2)

    for side, (title, items, color, res, is_rich) in enumerate([
            ("普通家庭的孩子", poor, POOR, poor_res, False),
            ("富裕家庭的孩子", rich, RICH, rich_res, True)]):
        x0 = 40 + side * (W // 2)
        cx = x0 + 120
        panel = fade((28, 32, 48), a)
        d.rounded_rectangle((x0, 100, x0 + W // 2 - 80, 560), 22, fill=panel, outline=fade(color, a * 0.6), width=2)
        d.text((x0 + 26, 116), title, font=F_HEAD, fill=fade(color, a))
        d.line((cx - 80, 470, cx + 80, 470), fill=fade((70, 74, 96), a), width=3)
        person(d, cx, 470, age, color, is_rich, gt + side, a)

        for i, s in enumerate(items):
            if not s:
                continue
            p = ease((lt - 1.2 - i * 1.6) / 0.6) * a
            if p <= 0:
                continue
            y = 190 + i * 80
            off = (1 - p) * 30
            tx = x0 + 240 + off
            d.ellipse((tx - 18, y + 10, tx - 8, y + 20), fill=fade(color, p))
            d.text((tx, y), s, font=F_ITEM, fill=fade((230, 232, 240), p))

        bp = ease((lt - 5.5) / 1.5) * a
        by = 500
        d.text((x0 + 26, by), "资源 / 选择", font=F_SMALL, fill=fade((170, 175, 195), a))
        bx0, bx1 = x0 + 150, x0 + W // 2 - 110
        d.rounded_rectangle((bx0, by + 4, bx1, by + 26), 11, fill=fade((45, 50, 70), a))
        fill_w = (bx1 - bx0) * res / 100 * bp
        if bp > 0:
            d.rounded_rectangle((bx0, by + 4, bx0 + max(22, fill_w), by + 26), 11, fill=fade(color, a * bp))

    cp = ease((lt - 7.0) / 0.8) * a
    if cp > 0:
        d.rounded_rectangle((140, 600, W - 140, 670), 20, fill=fade((34, 38, 56), cp))
        ctext(d, W / 2, 616, cap, F_CAP, fade((250, 236, 200), cp))
    ctext(d, W / 2, 690, "* 资源条为示意，非统计数据", F_SMALL, fade((100, 104, 124), a))
    return img


def draw_title(lt):
    a = ease(lt / 1.2) * (1 - ease((lt - (TITLE_DUR - 1.0)) / 1.0))
    img = BG_TITLE.copy()
    d = ImageDraw.Draw(img)
    bg = (20, 18, 34)
    ctext(d, W / 2, 230, "两个孩子的一生", F_TITLE, fade((250, 250, 255), a, bg))
    p = ease((lt - 1.5) / 1.0) * a
    ctext(d, W / 2, 330, "普通家庭  ×  富裕家庭", F_SUB, fade((200, 205, 230), p, bg))
    d.rounded_rectangle((W / 2 - 300, 400, W / 2 - 20, 410), 5, fill=fade(POOR, p, bg))
    d.rounded_rectangle((W / 2 + 20, 400, W / 2 + 300, 410), 5, fill=fade(RICH, p, bg))
    q = ease((lt - 3.5) / 1.0) * a
    ctext(d, W / 2, 460, "同一天出生，走向不同的人生轨迹", F_CAP, fade((170, 175, 200), q, bg))
    return img


def draw_end(lt):
    a = ease(lt / 1.2) * (1 - ease((lt - (END_DUR - 1.5)) / 1.5))
    img = BG_TITLE.copy()
    d = ImageDraw.Draw(img)
    bg = (20, 18, 34)
    lines = [
        ("出身决定起点，", F_TITLE, (250, 250, 255), 0.0, 190),
        ("但不决定终点。", F_TITLE, (250, 236, 200), 1.2, 280),
        ("教育、努力、品格与爱，", F_SUB, (200, 205, 230), 3.0, 420),
        ("是每个家庭都能给孩子的财富。", F_SUB, (200, 205, 230), 4.2, 470),
    ]
    for s, f, c, start, y in lines:
        p = ease((lt - start) / 1.0) * a
        if p > 0:
            ctext(d, W / 2, y + (1 - p) * 20, s, f, fade(c, p, bg))
    return img


def frame_at(t):
    if t < TITLE_DUR:
        return draw_title(t)
    t2 = t - TITLE_DUR
    idx = int(t2 // SCENE_DUR)
    if idx < len(SCENES):
        return draw_scene(idx, t2 - idx * SCENE_DUR, t)
    return draw_end(t2 - len(SCENES) * SCENE_DUR)


def make_music(path):
    sr = 44100
    n = int(TOTAL * sr)
    out = np.zeros(n)
    chords = [[261.6, 329.6, 392.0], [196.0, 246.9, 293.7], [220.0, 261.6, 329.6], [174.6, 220.0, 261.6]]
    beat = 0.5
    i = 0
    t = 0.0
    while t < TOTAL:
        chord = chords[(i // 8) % 4]
        f = chord[i % 3] * (2 if i % 8 in (3, 7) else 1)
        L = int(sr * 2.0)
        s = int(t * sr)
        e = min(n, s + L)
        tt = np.arange(e - s) / sr
        env = np.exp(-tt * 2.2) * np.minimum(1, tt * 200)
        out[s:e] += 0.18 * env * (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(4 * np.pi * f * tt))
        if i % 8 == 0:
            L2 = min(n - s, int(sr * 4))
            t3 = np.arange(L2) / sr
            out[s:s + L2] += 0.12 * np.exp(-t3 * 0.8) * np.sin(2 * np.pi * chord[0] / 2 * t3)
        i += 1
        t += beat
    fade_len = int(3 * sr)
    out[-fade_len:] *= np.linspace(1, 0, fade_len)
    out[:sr] *= np.linspace(0, 1, sr)
    out = out / np.max(np.abs(out)) * 0.5
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((out * 32767).astype(np.int16).tobytes())


def main():
    music = f"{OUT_DIR}/music.wav"
    make_music(music)
    out = f"{OUT_DIR}/两个孩子的一生.mp4"
    proc = subprocess.Popen([
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-i", music, "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart", out,
    ], stdin=subprocess.PIPE)
    frames = int(TOTAL * FPS)
    for k in range(frames):
        proc.stdin.write(frame_at(k / FPS).tobytes())
    proc.stdin.close()
    proc.wait()
    print(out, TOTAL, "seconds")


if __name__ == "__main__":
    main()
