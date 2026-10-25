/* VIBE知识大赏 · 拍视频赚钱的底层逻辑 · 1920×1080 · 无旁白 */
(() => {
  const W = 1920, H = 1080;
  const DURATION = 118;
  window.DURATION = DURATION;

  const C = {
    bg: "#070814",
    bg2: "#0d1024",
    gold: "#d4af6a",
    cream: "#f0e6d2",
    mute: "#8b879c",
    teal: "#6ed6b0",
    red: "#e85d5d",
    blue: "#6aa8ff",
    card: "#14182e",
    line: "rgba(212,175,106,0.35)",
  };

  // —— timing helpers ——
  const clamp = (x, a=0, b=1) => Math.max(a, Math.min(b, x));
  const lerp = (a, b, t) => a + (b - a) * t;
  const ease = (t) => { t = clamp(t); return t * t * (3 - 2 * t); };
  const easeOut = (t) => 1 - Math.pow(1 - clamp(t), 3);
  const easeIn = (t) => Math.pow(clamp(t), 3);
  const pulse = (t, speed=1) => 0.5 + 0.5 * Math.sin(t * speed);
  const frac = (t, a, b) => (b === a ? 0 : clamp((t - a) / (b - a)));
  const inRange = (t, a, b) => t >= a && t < b;
  const seeded = (n) => {
    const x = Math.sin(n * 127.1 + 311.7) * 43758.5453;
    return x - Math.floor(x);
  };

  // —— SFX event list (seconds, name) ——
  const SFX = [];
  const sfx = (t, name) => SFX.push([t, name]);
  window.getSfxEvents = () => SFX.slice();

  // —— Subtitles: [start, end, zh, en] ——
  const SUBS = [
    [0.4, 3.2, "有人一条视频赚几百，有人赚几万", "Some make hundreds. Some make tens of thousands."],
    [3.3, 6.2, "差别，不在镜头——在玩的游戏不同", "The gap isn't the lens. It's the game."],
    [14.2, 17.2, "短视频越火，摄影师未必越赚钱", "More short video ≠ more pay for shooters."],
    [17.3, 20.8, "观看的人更多，生产门槛却更低", "More viewers. Lower production barrier."],
    [21.0, 24.6, "拍视频赚钱，其实是五种完全不同的游戏", "Making money with video is five different games."],
    [24.8, 28.4, "卖制作 · 卖传播 · 卖成交 · 卖授权 · 卖系统", "Craft · Reach · Conversion · Rights · Systems"],
    [28.6, 32.4, "你主要在第一种里，却羡慕第三、第五种的收入", "You’re in Game 1, eyeing Games 3 & 5."],
    [32.6, 36.4, "人家未必拍得更牛，只是没锁死「拍完收一次钱」", "They may not shoot better—just don’t bill once."],
    [36.6, 40.4, "播放量是注意力，不是人民币", "Views are attention. Not RMB."],
    [40.6, 44.8, "100万播放可能 0 单 · 3000播放可能 5 单", "1M views → 0 orders. 3K views → 5 orders."],
    [45.0, 49.0, "平台喜欢的视频，不一定最能帮商家赚钱", "What platforms love ≠ what stores need."],
    [49.2, 53.2, "客户买的未必是视频，而是一个「购买理由」", "Clients don’t buy footage. They buy a reason."],
    [53.4, 57.4, "先问：客户为什么还没买你的东西？", "Ask first: why haven’t they bought yet?"],
    [57.6, 61.6, "商业短视频的作用之一：减少购买阻力", "One job of commercial video: cut friction."],
    [61.8, 66.0, "一条视频，可以不只卖一次", "One video can sell more than once."],
    [66.2, 70.4, "制作费 · 发布费 · 广告授权 · 原素材——分开谈", "Fee · Posting · Ad rights · Raws—name each."],
    [70.6, 74.8, "付款拍摄 ≠ 版权与商用自动全部转让", "Paying for a shoot != owning every right."],
    [75.0, 79.2, "真正昂贵的，可能是「进入现场的资格」", "What’s scarce: permission to enter the room."],
    [79.4, 83.6, "AI能生成豪华餐厅，却替代不了真实后厨", "AI can fake luxury. Not a real kitchen."],
    [83.8, 88.0, "护城河从「制造画面」迁到「真实记录」", "Moat shifts: inventing shots → recording truth."],
    [88.2, 92.4, "营业额很高，时薪可能很低", "High revenue. Tiny hourly rate."],
    [92.6, 96.8, "¥2000 项目 ÷ 22 小时 ≈ ¥77 / 时", "¥2000 ÷ 22h ≈ ¥77 / hour."],
    [97.0, 101.0, "无限修改不是好服务，是无限下注不确定性", "Unlimited revisions ≠ good service."],
    [101.2, 105.4, "真正的工作室，卖的是可测试的商业假设", "Real studios sell testable hypotheses."],
    [105.6, 109.6, "同一产品，测三种购买理由", "One product. Three reasons. Test them."],
    [109.8, 113.6, "拿起相机前，先想清：这条片承担什么任务", "Before you shoot: what job does this clip do?"],
    [113.8, 117.6, "从会拍视频的人，变成懂视频生意的人", "From shooter → someone who gets the business."],
  ];

  // —— Top labels ——
  const LABELS = [
    [0, 6.2, "反常识开场"],
    [14, 20.8, "行业现实 · 2026"],
    [21, 36.4, "五种赚钱游戏"],
    [36.6, 49, "注意力 ≠ 现金"],
    [49.2, 61.6, "购买理由"],
    [61.8, 74.8, "内容使用权"],
    [75, 88, "现场资格"],
    [88.2, 101, "时薪陷阱"],
    [101.2, 109.6, "可测试假设"],
    [109.8, 118, "收束"],
  ];

  // Register SFX on key beats
  [[0.5,"whoosh"],[3.3,"tick"],[6.5,"boom"],[14.2,"whoosh"],[21,"tick"],[24.8,"pop"],
   [28.6,"whoosh"],[36.6,"boom"],[40.6,"coin"],[45,"tick"],[49.2,"whoosh"],[53.4,"tick"],
   [57.6,"soft"],[61.8,"boom"],[66.2,"stamp"],[70.6,"tick"],[75,"whoosh"],[79.4,"soft"],
   [83.8,"tick"],[88.2,"boom"],[92.6,"coin"],[97,"tick"],[101.2,"whoosh"],[105.6,"pop"],
   [109.8,"soft"],[113.8,"boom"]].forEach(([t,n]) => sfx(t,n));

  // —— drawing primitives ——
  function bg(ctx, t) {
    const g = ctx.createRadialGradient(W*0.5, H*0.35, 80, W*0.5, H*0.5, 1100);
    g.addColorStop(0, "#12162c");
    g.addColorStop(0.55, C.bg2);
    g.addColorStop(1, C.bg);
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, W, H);
    // floating gold dust
    for (let i = 0; i < 48; i++) {
      const x = (seeded(i) * W + Math.sin(t*0.2 + i) * 30) % W;
      const y = (seeded(i+9) * H + t * (8 + seeded(i)*20)) % H;
      ctx.globalAlpha = 0.08 + 0.12 * seeded(i+3);
      ctx.fillStyle = C.gold;
      ctx.beginPath();
      ctx.arc(x, y, 1.2 + seeded(i+2)*1.8, 0, Math.PI*2);
      ctx.fill();
    }
    ctx.globalAlpha = 1;
    // vignette
    const v = ctx.createRadialGradient(W/2, H/2, 400, W/2, H/2, 1100);
    v.addColorStop(0, "rgba(0,0,0,0)");
    v.addColorStop(1, "rgba(0,0,0,0.55)");
    ctx.fillStyle = v;
    ctx.fillRect(0, 0, W, H);
  }

  function roundRect(ctx, x, y, w, h, r) {
    ctx.beginPath();
    ctx.moveTo(x+r, y);
    ctx.arcTo(x+w, y, x+w, y+h, r);
    ctx.arcTo(x+w, y+h, x, y+h, r);
    ctx.arcTo(x, y+h, x, y, r);
    ctx.arcTo(x, y, x+w, y, r);
    ctx.closePath();
  }

  function phone(ctx, x, y, s, opts={}) {
    const w = 160*s, h = 300*s, r = 22*s;
    ctx.save();
    ctx.translate(x, y);
    // body
    ctx.fillStyle = "#1a1e33";
    roundRect(ctx, -w/2, -h/2, w, h, r);
    ctx.fill();
    ctx.strokeStyle = "rgba(240,230,210,0.25)";
    ctx.lineWidth = 2;
    ctx.stroke();
    // screen
    ctx.fillStyle = opts.screen || "#0b0e1c";
    roundRect(ctx, -w/2+8*s, -h/2+28*s, w-16*s, h-56*s, 10*s);
    ctx.fill();
    // notch
    ctx.fillStyle = "#0a0c16";
    roundRect(ctx, -28*s, -h/2+10*s, 56*s, 10*s, 5*s);
    ctx.fill();
    ctx.restore();
  }

  function drawBill(ctx, x, y, s, alpha=1) {
    ctx.save();
    ctx.globalAlpha = alpha;
    ctx.translate(x, y);
    ctx.scale(s, s);
    ctx.fillStyle = C.teal;
    roundRect(ctx, -28, -14, 56, 28, 4);
    ctx.fill();
    ctx.strokeStyle = "rgba(7,8,20,0.35)";
    ctx.stroke();
    ctx.fillStyle = "#073028";
    ctx.font = "bold 14px 'Noto Sans SC', sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText("¥", 0, 1);
    ctx.restore();
  }

  function cameraBody(ctx, x, y, s, ang=0) {
    ctx.save();
    ctx.translate(x, y);
    ctx.rotate(ang);
    ctx.scale(s, s);
    // body
    ctx.fillStyle = "#22283f";
    roundRect(ctx, -70, -40, 110, 80, 10);
    ctx.fill();
    ctx.fillStyle = "#161a2c";
    roundRect(ctx, -55, -28, 50, 40, 6);
    ctx.fill();
    // lens
    ctx.beginPath();
    ctx.arc(55, 0, 34, 0, Math.PI*2);
    ctx.fillStyle = "#2a314d";
    ctx.fill();
    ctx.beginPath();
    ctx.arc(55, 0, 22, 0, Math.PI*2);
    ctx.fillStyle = "#0c1020";
    ctx.fill();
    ctx.beginPath();
    ctx.arc(55, 0, 10, 0, Math.PI*2);
    ctx.fillStyle = C.gold;
    ctx.globalAlpha = 0.55;
    ctx.fill();
    ctx.globalAlpha = 1;
    // flash
    ctx.fillStyle = C.cream;
    roundRect(ctx, -60, -50, 18, 10, 3);
    ctx.fill();
    ctx.restore();
  }

  function topLabel(ctx, t) {
    let text = "";
    for (const [a,b,s] of LABELS) if (t >= a && t < b) text = s;
    if (!text) return;
    ctx.fillStyle = C.gold;
    ctx.font = "500 22px 'Noto Sans SC', sans-serif";
    ctx.textAlign = "left";
    ctx.textBaseline = "top";
    ctx.globalAlpha = 0.9;
    ctx.fillText(text, 72, 48);
    ctx.globalAlpha = 0.35;
    ctx.fillStyle = C.line;
    ctx.fillRect(72, 78, 220, 1);
    ctx.globalAlpha = 1;
    // series mark
    ctx.fillStyle = C.mute;
    ctx.font = "500 16px 'Noto Sans SC', sans-serif";
    ctx.textAlign = "right";
    ctx.fillText("VIBE 知识大赏", W - 72, 52);
  }

  function subtitle(ctx, t) {
    let cur = null;
    for (const s of SUBS) if (t >= s[0] && t < s[1]) cur = s;
    if (!cur) return;
    const [a, b, zh, en] = cur;
    const local = t - a;
    const fade = local < 0.25 ? ease(local/0.25) : (b - t < 0.25 ? ease((b-t)/0.25) : 1);
    ctx.globalAlpha = fade;
    ctx.fillStyle = C.cream;
    ctx.font = "600 36px 'Noto Serif SC', serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "alphabetic";
    ctx.fillText(zh, W/2, H - 92);
    ctx.fillStyle = C.mute;
    ctx.font = "italic 500 24px 'Noto Serif SC', serif";
    ctx.fillText(en, W/2, H - 52);
    ctx.globalAlpha = 1;
  }

  // —— SCENES ——
  function sceneHook(ctx, t) {
    // 0–6.4: two phones
    const p = easeOut(frac(t, 0, 1.2));
    const leftX = lerp(-200, 620, p);
    const rightX = lerp(W+200, 1300, p);
    const y = 400;

    // left phone: viral / 0 money
    phone(ctx, leftX, y, 1.35, { screen: "#151a30" });
    ctx.save();
    ctx.beginPath();
    roundRect(ctx, leftX - 90, y - 160, 180, 250, 12);
    ctx.clip();
    // fake feed
    ctx.fillStyle = "#1e2540";
    ctx.fillRect(leftX - 90, y - 160, 180, 250);
    for (let i = 0; i < 5; i++) {
      const yy = y - 140 + i * 48 + (t * 18) % 48;
      ctx.fillStyle = i % 2 ? "#2a3355" : "#24304c";
      roundRect(ctx, leftX - 74, yy, 148, 36, 6);
      ctx.fill();
    }
    ctx.restore();
    // views badge
    ctx.fillStyle = C.gold;
    ctx.font = "700 28px 'Noto Sans SC', sans-serif";
    ctx.textAlign = "center";
    ctx.fillText("100万播放", leftX, y + 210);
    ctx.fillStyle = C.red;
    ctx.font = "700 42px 'Noto Serif SC', serif";
    ctx.fillText("¥ 0", leftX, y + 255);
    // falling zeros
    for (let i = 0; i < 8; i++) {
      const yy = y + 100 + ((t * 60 + i * 40) % 200);
      ctx.globalAlpha = 0.35;
      ctx.fillStyle = C.red;
      ctx.font = "700 20px 'Noto Sans SC', sans-serif";
      ctx.fillText("0", leftX + Math.sin(i + t)*40, yy);
    }
    ctx.globalAlpha = 1;

    // right phone: precise / money
    phone(ctx, rightX, y, 1.35, { screen: "#10241c" });
    ctx.save();
    ctx.beginPath();
    roundRect(ctx, rightX - 90, y - 160, 180, 250, 12);
    ctx.clip();
    ctx.fillStyle = "#143228";
    ctx.fillRect(rightX - 90, y - 160, 180, 250);
    // badminton court lines (concrete)
    ctx.strokeStyle = C.teal;
    ctx.lineWidth = 2;
    ctx.strokeRect(rightX - 60, y - 100, 120, 160);
    ctx.beginPath();
    ctx.moveTo(rightX, y - 100);
    ctx.lineTo(rightX, y + 60);
    ctx.stroke();
    // shuttlecock
    ctx.fillStyle = C.cream;
    ctx.beginPath();
    ctx.arc(rightX + Math.sin(t*2)*20, y - 20 + Math.cos(t*3)*10, 8, 0, Math.PI*2);
    ctx.fill();
    ctx.restore();
    ctx.fillStyle = C.mute;
    ctx.font = "700 28px 'Noto Sans SC', sans-serif";
    ctx.textAlign = "center";
    ctx.fillText("3000播放", rightX, y + 210);
    ctx.fillStyle = C.teal;
    ctx.font = "700 42px 'Noto Serif SC', serif";
    ctx.fillText("5 单 · ¥3500", rightX, y + 255);

    // bills flying into right phone after 2s
    if (t > 2) {
      for (let i = 0; i < 10; i++) {
        const tt = frac(t, 2 + i*0.12, 4.5);
        const bx = lerp(rightX + 180, rightX, easeOut(tt));
        const by = lerp(y - 80 - i*10, y, easeOut(tt));
        drawBill(ctx, bx, by, 1.1, easeOut(tt));
      }
    }

    // vs
    ctx.globalAlpha = p;
    ctx.fillStyle = C.gold;
    ctx.font = "700 48px 'Noto Serif SC', serif";
    ctx.textAlign = "center";
    ctx.fillText("VS", W/2, y);
    ctx.globalAlpha = 1;
  }

  function sceneTitle(ctx, t) {
    // 6.4–14
    const local = t - 6.4;
    const a = easeOut(frac(local, 0, 0.8));
    ctx.globalAlpha = a;
    ctx.fillStyle = C.gold;
    ctx.font = "600 22px 'Noto Sans SC', sans-serif";
    ctx.textAlign = "center";
    ctx.fillText("VIBE 知识大赏", W/2, 320);
    ctx.fillStyle = C.cream;
    ctx.font = "800 72px 'Noto Serif SC', serif";
    ctx.fillText("拍视频赚钱的底层逻辑", W/2, 430);
    ctx.fillStyle = C.mute;
    ctx.font = "italic 400 26px 'Noto Serif SC', serif";
    ctx.fillText("Not the golden 3 seconds. Not daily persona posts.", W/2, 500);
    // underline draw
    const uw = easeOut(frac(local, 0.6, 1.6)) * 520;
    ctx.strokeStyle = C.gold;
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(W/2 - uw/2, 460);
    ctx.lineTo(W/2 + uw/2, 460);
    ctx.stroke();
    // orbiting camera
    const ang = local * 0.7;
    cameraBody(ctx, W/2 + Math.cos(ang)*260, 620 + Math.sin(ang)*40, 1.1, ang*0.2);
    ctx.globalAlpha = 1;
    // fade out
    if (local > 6.5) {
      ctx.globalAlpha = ease(frac(local, 6.5, 7.5));
      ctx.fillStyle = C.bg;
      ctx.fillRect(0, 0, W, H);
      ctx.globalAlpha = 1;
    }
  }

  function sceneIndustry(ctx, t) {
    // 14–21: user growth vs AI flood
    const local = t - 14;
    // left: people icons growing
    ctx.fillStyle = C.cream;
    ctx.font = "700 28px 'Noto Sans SC', sans-serif";
    ctx.textAlign = "center";
    ctx.fillText("短视频用户", 520, 260);
    const nPeople = Math.floor(easeOut(frac(local, 0, 3)) * 48);
    for (let i = 0; i < nPeople; i++) {
      const col = i % 8, row = Math.floor(i / 8);
      const x = 320 + col * 50, y = 320 + row * 55;
      ctx.fillStyle = C.blue;
      ctx.beginPath();
      ctx.arc(x, y, 12, 0, Math.PI*2);
      ctx.fill();
      ctx.fillRect(x - 8, y + 14, 16, 18);
    }
    ctx.fillStyle = C.gold;
    ctx.font = "800 48px 'Noto Serif SC', serif";
    ctx.fillText("10.74亿", 520, 700);

    // right: AI frames multiplying
    ctx.fillStyle = C.cream;
    ctx.font = "700 28px 'Noto Sans SC', sans-serif";
    ctx.fillText("AI生成音视频", 1400, 260);
    const nAI = Math.floor(easeOut(frac(local, 0.5, 3.5)) * 36);
    for (let i = 0; i < nAI; i++) {
      const col = i % 6, row = Math.floor(i / 6);
      const x = 1220 + col * 58 + seeded(i)*6;
      const y = 300 + row * 58;
      ctx.strokeStyle = C.gold;
      ctx.globalAlpha = 0.5 + 0.5*seeded(i);
      ctx.lineWidth = 2;
      roundRect(ctx, x, y, 44, 44, 6);
      ctx.stroke();
      // sparkle A
      ctx.fillStyle = C.gold;
      ctx.font = "700 16px 'Noto Sans SC', sans-serif";
      ctx.fillText("AI", x + 22, y + 28);
    }
    ctx.globalAlpha = 1;
    ctx.fillStyle = C.red;
    ctx.font = "800 48px 'Noto Serif SC', serif";
    ctx.fillText("暴增 14×+", 1400, 700);

    // arrow down on unit price
    if (local > 3.5) {
      const a = easeOut(frac(local, 3.5, 5));
      ctx.globalAlpha = a;
      ctx.strokeStyle = C.red;
      ctx.lineWidth = 4;
      ctx.beginPath();
      ctx.moveTo(W/2, 300);
      ctx.lineTo(W/2, 520);
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(W/2 - 20, 500);
      ctx.lineTo(W/2, 530);
      ctx.lineTo(W/2 + 20, 500);
      ctx.stroke();
      ctx.fillStyle = C.cream;
      ctx.font = "600 28px 'Noto Sans SC', sans-serif";
      ctx.textAlign = "center";
      ctx.fillText("部分岗位单价仍可能下降", W/2, 580);
      ctx.globalAlpha = 1;
    }
  }

  function sceneFiveGames(ctx, t) {
    // 21–36.5
    const local = t - 21;
    const games = [
      { name: "卖制作", icon: "相机", color: C.blue },
      { name: "卖传播", icon: "喇叭", color: C.gold },
      { name: "卖成交", icon: "收银", color: C.teal },
      { name: "卖授权", icon: "印章", color: "#c99bff" },
      { name: "卖系统", icon: "流水线", color: "#ff9b6a" },
    ];
    const appear = easeOut(frac(local, 0, 1.2));
    games.forEach((g, i) => {
      const x = 220 + i * 370;
      const y = 420;
      const a = easeOut(frac(local, i * 0.25, i * 0.25 + 0.8));
      ctx.globalAlpha = a * appear;
      // arcade / card cabinet
      ctx.fillStyle = C.card;
      roundRect(ctx, x - 130, y - 180, 260, 320, 18);
      ctx.fill();
      ctx.strokeStyle = g.color;
      ctx.lineWidth = 2;
      ctx.stroke();
      // icon area
      ctx.fillStyle = g.color;
      ctx.globalAlpha = a * 0.2;
      roundRect(ctx, x - 90, y - 130, 180, 120, 12);
      ctx.fill();
      ctx.globalAlpha = a * appear;
      if (i === 0) cameraBody(ctx, x, y - 70, 0.7);
      else if (i === 1) {
        // megaphone
        ctx.fillStyle = g.color;
        ctx.beginPath();
        ctx.moveTo(x - 40, y - 90);
        ctx.lineTo(x + 50, y - 110);
        ctx.lineTo(x + 50, y - 30);
        ctx.lineTo(x - 40, y - 50);
        ctx.closePath();
        ctx.fill();
        ctx.beginPath();
        ctx.arc(x - 50, y - 70, 22, 0, Math.PI*2);
        ctx.fill();
      } else if (i === 2) {
        // cash register
        ctx.fillStyle = g.color;
        roundRect(ctx, x - 55, y - 100, 110, 70, 8);
        ctx.fill();
        ctx.fillStyle = C.bg;
        roundRect(ctx, x - 40, y - 88, 80, 28, 4);
        ctx.fill();
        drawBill(ctx, x, y - 40, 1.2);
      } else if (i === 3) {
        // stamp
        ctx.strokeStyle = g.color;
        ctx.lineWidth = 4;
        ctx.beginPath();
        ctx.arc(x, y - 70, 40, 0, Math.PI*2);
        ctx.stroke();
        ctx.fillStyle = g.color;
        ctx.font = "700 22px 'Noto Sans SC', sans-serif";
        ctx.textAlign = "center";
        ctx.fillText("授权", x, y - 62);
      } else {
        // pipeline boxes
        for (let k = 0; k < 3; k++) {
          ctx.fillStyle = g.color;
          roundRect(ctx, x - 70 + k * 50, y - 100, 40, 40, 6);
          ctx.fill();
          if (k < 2) {
            ctx.strokeStyle = C.cream;
            ctx.beginPath();
            ctx.moveTo(x - 28 + k * 50, y - 80);
            ctx.lineTo(x - 20 + k * 50, y - 80);
            ctx.stroke();
          }
        }
      }
      ctx.fillStyle = C.cream;
      ctx.font = "700 32px 'Noto Serif SC', serif";
      ctx.textAlign = "center";
      ctx.fillText(g.name, x, y + 60);
      ctx.fillStyle = C.mute;
      ctx.font = "500 18px 'Noto Sans SC', sans-serif";
      ctx.fillText("第 " + (i+1) + " 种", x, y + 100);
      ctx.globalAlpha = 1;

      // highlight you're in #1, envy 3 and 5
      if (local > 7.5) {
        const h = easeOut(frac(local, 7.5, 9));
        if (i === 0) {
          ctx.globalAlpha = h;
          ctx.strokeStyle = C.blue;
          ctx.lineWidth = 4;
          roundRect(ctx, x - 140, y - 190, 280, 340, 20);
          ctx.stroke();
          ctx.fillStyle = C.blue;
          ctx.font = "700 22px 'Noto Sans SC', sans-serif";
          ctx.fillText("你在这里", x, y + 140);
        }
        if (i === 2 || i === 4) {
          ctx.globalAlpha = h * (0.6 + 0.4*pulse(t, 3));
          ctx.fillStyle = C.gold;
          ctx.font = "700 20px 'Noto Sans SC', sans-serif";
          ctx.fillText("收入更高？", x, y - 200);
        }
        ctx.globalAlpha = 1;
      }
    });
  }

  function sceneViewsMoney(ctx, t) {
    // 36.5–49
    const local = t - 36.5;
    // left pile of eyes
    ctx.fillStyle = C.cream;
    ctx.font = "700 30px 'Noto Sans SC', sans-serif";
    ctx.textAlign = "center";
    ctx.fillText("注意力", 520, 250);
    const eyes = Math.floor(easeOut(frac(local, 0, 2)) * 40);
    for (let i = 0; i < eyes; i++) {
      const x = 320 + (i % 8) * 50 + seeded(i)*8;
      const y = 300 + Math.floor(i/8) * 55;
      // eye
      ctx.fillStyle = C.blue;
      ctx.beginPath();
      ctx.ellipse(x, y, 18, 11, 0, 0, Math.PI*2);
      ctx.fill();
      ctx.fillStyle = C.bg;
      ctx.beginPath();
      ctx.arc(x, y, 5, 0, Math.PI*2);
      ctx.fill();
    }
    ctx.fillStyle = C.gold;
    ctx.font = "800 40px 'Noto Serif SC', serif";
    ctx.fillText("100万播放", 520, 680);
    ctx.fillStyle = C.red;
    ctx.fillText("订单 0", 520, 740);

    // conversion
    if (local > 2) {
      const a = easeOut(frac(local, 2, 3.5));
      ctx.globalAlpha = a;
      ctx.strokeStyle = C.gold;
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.moveTo(760, 480);
      ctx.lineTo(980, 480);
      ctx.stroke();
      ctx.fillStyle = C.gold;
      ctx.font = "700 24px 'Noto Sans SC', sans-serif";
      ctx.fillText("≠ 自动变现", W/2 - 40, 450);
      ctx.globalAlpha = 1;
    }

    // right: few eyes + money
    ctx.fillStyle = C.cream;
    ctx.font = "700 30px 'Noto Sans SC', sans-serif";
    ctx.fillText("成交", 1400, 250);
    const few = Math.floor(easeOut(frac(local, 1, 2.5)) * 6);
    for (let i = 0; i < few; i++) {
      const x = 1280 + i * 50;
      ctx.fillStyle = C.teal;
      ctx.beginPath();
      ctx.ellipse(x, 340, 18, 11, 0, 0, Math.PI*2);
      ctx.fill();
      ctx.fillStyle = C.bg;
      ctx.beginPath();
      ctx.arc(x, 340, 5, 0, Math.PI*2);
      ctx.fill();
    }
    const bills = Math.floor(easeOut(frac(local, 2.5, 5)) * 12);
    for (let i = 0; i < bills; i++) {
      drawBill(ctx, 1300 + (i%4)*55, 420 + Math.floor(i/4)*45, 1.3);
    }
    ctx.fillStyle = C.mute;
    ctx.font = "800 40px 'Noto Serif SC', serif";
    ctx.fillText("3000播放", 1400, 680);
    ctx.fillStyle = C.teal;
    ctx.fillText("5单 · ¥3500", 1400, 740);
  }

  function sceneBuyReason(ctx, t) {
    // 49–61.8
    const local = t - 49;
    // parent figure + child + badminton coach
    // parent
    ctx.fillStyle = "#c4b59a";
    ctx.beginPath();
    ctx.arc(480, 340, 36, 0, Math.PI*2);
    ctx.fill();
    ctx.fillStyle = "#3d4a6b";
    roundRect(ctx, 440, 380, 80, 110, 12);
    ctx.fill();
    // child
    ctx.fillStyle = "#e8c9a0";
    ctx.beginPath();
    ctx.arc(620, 400, 26, 0, Math.PI*2);
    ctx.fill();
    ctx.fillStyle = "#5a6a90";
    roundRect(ctx, 592, 428, 56, 80, 10);
    ctx.fill();
    // coach
    ctx.fillStyle = "#8fd6b5";
    ctx.beginPath();
    ctx.arc(1180, 360, 34, 0, Math.PI*2);
    ctx.fill();
    ctx.fillStyle = "#1f6b52";
    roundRect(ctx, 1140, 400, 80, 120, 12);
    ctx.fill();
    // racket
    ctx.strokeStyle = C.gold;
    ctx.lineWidth = 4;
    ctx.beginPath();
    ctx.ellipse(1240, 360, 28, 40, 0.3, 0, Math.PI*2);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(1220, 395);
    ctx.lineTo(1200, 470);
    ctx.stroke();

    // hesitation bubbles
    const fears = ["教练负责吗？", "跟得上吗？", "值不值？", "环境怎样？"];
    fears.forEach((f, i) => {
      const a = easeOut(frac(local, 0.4 + i*0.35, 1.2 + i*0.35));
      const x = 700 + (i%2)*160;
      const y = 280 + Math.floor(i/2)*90;
      ctx.globalAlpha = a;
      ctx.fillStyle = C.card;
      roundRect(ctx, x, y, 150, 54, 12);
      ctx.fill();
      ctx.strokeStyle = C.red;
      ctx.stroke();
      ctx.fillStyle = C.cream;
      ctx.font = "600 18px 'Noto Sans SC', sans-serif";
      ctx.textAlign = "center";
      ctx.fillText(f, x + 75, y + 34);
      ctx.globalAlpha = 1;
    });

    // video card removes barriers
    if (local > 4) {
      const a = easeOut(frac(local, 4, 5.5));
      ctx.globalAlpha = a;
      // film strip
      ctx.fillStyle = "#1a2038";
      roundRect(ctx, 760, 520, 400, 160, 14);
      ctx.fill();
      ctx.fillStyle = C.gold;
      ctx.font = "700 24px 'Noto Sans SC', sans-serif";
      ctx.textAlign = "center";
      ctx.fillText("真实第一节课 · 教练带零基础", 960, 580);
      ctx.fillStyle = C.teal;
      ctx.font = "600 20px 'Noto Sans SC', sans-serif";
      ctx.fillText("证据 · 解释 · 体验 → 更愿咨询", 960, 630);
      // barriers fade
      const fade = easeOut(frac(local, 5.5, 7.5));
      fears.forEach((_, i) => {
        // checkmarks overlay conceptually by reducing fear opacity already gone
      });
      ctx.fillStyle = C.teal;
      ctx.font = "700 28px 'Noto Sans SC', sans-serif";
      ctx.fillText("购买阻力 ↓", 960, 720);
      ctx.globalAlpha = 1;
    }
  }

  function sceneRights(ctx, t) {
    // 61.8–75
    const local = t - 61.8;
    // one film strip in center
    ctx.fillStyle = "#1a2038";
    roundRect(ctx, 760, 280, 400, 220, 16);
    ctx.fill();
    ctx.fillStyle = C.cream;
    ctx.font = "700 28px 'Noto Sans SC', sans-serif";
    ctx.textAlign = "center";
    ctx.fillText("一条成片", 960, 400);
    // sprocket holes
    for (let i = 0; i < 6; i++) {
      ctx.fillStyle = C.bg;
      roundRect(ctx, 780 + i * 60, 300, 16, 24, 3);
      ctx.fill();
      roundRect(ctx, 780 + i * 60, 460, 16, 24, 3);
      ctx.fill();
    }

    const rights = [
      { n: "制作费", x: 320, y: 360 },
      { n: "发布费", x: 320, y: 520 },
      { n: "广告授权", x: 1600, y: 360 },
      { n: "原素材", x: 1600, y: 520 },
    ];
    rights.forEach((r, i) => {
      const a = easeOut(frac(local, 1 + i*0.4, 2 + i*0.4));
      ctx.globalAlpha = a;
      ctx.strokeStyle = C.gold;
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(960, 390);
      ctx.lineTo(r.x, r.y);
      ctx.stroke();
      // stamp
      ctx.fillStyle = C.card;
      ctx.beginPath();
      ctx.arc(r.x, r.y, 70, 0, Math.PI*2);
      ctx.fill();
      ctx.strokeStyle = C.gold;
      ctx.lineWidth = 3;
      ctx.stroke();
      ctx.fillStyle = C.gold;
      ctx.font = "700 24px 'Noto Sans SC', sans-serif";
      ctx.textAlign = "center";
      ctx.fillText(r.n, r.x, r.y + 8);
      drawBill(ctx, r.x, r.y + 90, 1.1, a);
      ctx.globalAlpha = 1;
    });

    if (local > 7) {
      const a = easeOut(frac(local, 7, 8.5));
      ctx.globalAlpha = a;
      ctx.fillStyle = C.red;
      ctx.font = "700 32px 'Noto Serif SC', serif";
      ctx.textAlign = "center";
      ctx.fillText("付款拍摄 ≠ 全部权利自动转让", W/2, 720);
      ctx.globalAlpha = 1;
    }
  }

  function sceneAccess(ctx, t) {
    // 75–88.2
    const local = t - 75;
    // left: AI generated fancy restaurant (fake sparkles)
    ctx.fillStyle = C.card;
    roundRect(ctx, 180, 240, 600, 420, 20);
    ctx.fill();
    ctx.fillStyle = C.gold;
    ctx.font = "700 26px 'Noto Sans SC', sans-serif";
    ctx.textAlign = "center";
    ctx.fillText("AI 生成的豪华餐厅", 480, 290);
    // fake glamorous table
    for (let i = 0; i < 12; i++) {
      const x = 280 + (i%4)*100 + Math.sin(t+i)*4;
      const y = 360 + Math.floor(i/4)*80;
      ctx.fillStyle = `hsla(${40+i*5},70%,55%,0.7)`;
      ctx.beginPath();
      ctx.arc(x, y, 22, 0, Math.PI*2);
      ctx.fill();
    }
    ctx.fillStyle = C.mute;
    ctx.font = "600 22px 'Noto Sans SC', sans-serif";
    ctx.fillText("漂亮，但无法证明卫生与手艺", 480, 620);

    // right: real kitchen door with access badge
    ctx.fillStyle = "#1a2220";
    roundRect(ctx, 1140, 240, 600, 420, 20);
    ctx.fill();
    // door
    ctx.fillStyle = "#2a3530";
    roundRect(ctx, 1320, 320, 240, 280, 8);
    ctx.fill();
    ctx.fillStyle = C.gold;
    ctx.beginPath();
    ctx.arc(1520, 460, 10, 0, Math.PI*2);
    ctx.fill();
    // steam
    for (let i = 0; i < 5; i++) {
      ctx.globalAlpha = 0.25;
      ctx.strokeStyle = C.cream;
      ctx.beginPath();
      const x = 1380 + i*30;
      ctx.moveTo(x, 400);
      ctx.quadraticCurveTo(x + Math.sin(t*2+i)*10, 360, x, 320 - (t*20+i*10)%40);
      ctx.stroke();
    }
    ctx.globalAlpha = 1;
    // badge
    const a = easeOut(frac(local, 1.5, 3));
    ctx.globalAlpha = a;
    ctx.fillStyle = C.teal;
    roundRect(ctx, 1260, 300, 120, 70, 10);
    ctx.fill();
    ctx.fillStyle = C.bg;
    ctx.font = "700 20px 'Noto Sans SC', sans-serif";
    ctx.textAlign = "center";
    ctx.fillText("拍摄许可", 1320, 342);
    ctx.globalAlpha = 1;
    ctx.fillStyle = C.cream;
    ctx.font = "700 26px 'Noto Sans SC', sans-serif";
    ctx.fillText("真实后厨 · 真实教学 · 真实老板", 1440, 290);
    ctx.fillStyle = C.teal;
    ctx.font = "600 22px 'Noto Sans SC', sans-serif";
    ctx.fillText("别人坐家里生成不了的证据", 1440, 620);
  }

  function sceneHourly(ctx, t) {
    // 88.2–101.2
    const local = t - 88.2;
    // big clock
    ctx.strokeStyle = C.gold;
    ctx.lineWidth = 6;
    ctx.beginPath();
    ctx.arc(W/2, 420, 180, 0, Math.PI*2);
    ctx.stroke();
    ctx.fillStyle = C.card;
    ctx.beginPath();
    ctx.arc(W/2, 420, 170, 0, Math.PI*2);
    ctx.fill();
    // hands spinning faster
    const ang = t * 2.2;
    ctx.strokeStyle = C.cream;
    ctx.lineWidth = 5;
    ctx.beginPath();
    ctx.moveTo(W/2, 420);
    ctx.lineTo(W/2 + Math.cos(ang)*120, 420 + Math.sin(ang)*120);
    ctx.stroke();
    ctx.strokeStyle = C.gold;
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(W/2, 420);
    ctx.lineTo(W/2 + Math.cos(ang*12)*80, 420 + Math.sin(ang*12)*80);
    ctx.stroke();

    // money eaten by clock
    const eaten = easeOut(frac(local, 0.5, 4));
    ctx.fillStyle = C.gold;
    ctx.font = "800 56px 'Noto Serif SC', serif";
    ctx.textAlign = "center";
    ctx.fillText("¥" + Math.round(lerp(2000, 77, eaten)), W/2, 700);
    ctx.fillStyle = C.mute;
    ctx.font = "600 24px 'Noto Sans SC', sans-serif";
    ctx.fillText("项目报价 → 真实时薪", W/2, 750);

    // side stats
    const stats = [
      { n: "拍摄 4h", x: 320 },
      { n: "剪辑 8h", x: 320 },
      { n: "返工 6h", x: 1600 },
      { n: "沟通 4h", x: 1600 },
    ];
    stats.forEach((s, i) => {
      const a = easeOut(frac(local, 0.3+i*0.3, 1.3+i*0.3));
      const y = 300 + (i%2)*120;
      ctx.globalAlpha = a;
      ctx.fillStyle = C.card;
      roundRect(ctx, s.x - 110, y, 220, 70, 12);
      ctx.fill();
      ctx.fillStyle = C.cream;
      ctx.font = "600 26px 'Noto Sans SC', sans-serif";
      ctx.textAlign = "center";
      ctx.fillText(s.n, s.x, y + 44);
      ctx.globalAlpha = 1;
    });
  }

  function sceneHypothesis(ctx, t) {
    // 101.2–109.8
    const local = t - 101.2;
    // three milk tea cups with different labels
    const labels = ["新鲜现制", "第二杯半价", "适合办公续命"];
    const colors = [C.gold, C.teal, C.blue];
    labels.forEach((lab, i) => {
      const x = 480 + i * 480;
      const a = easeOut(frac(local, i*0.4, 1 + i*0.4));
      const lift = Math.sin(t * 2 + i) * 8;
      ctx.globalAlpha = a;
      // cup
      ctx.fillStyle = colors[i];
      ctx.globalAlpha = a * 0.85;
      ctx.beginPath();
      ctx.moveTo(x - 50, 320 + lift);
      ctx.lineTo(x - 40, 520 + lift);
      ctx.lineTo(x + 40, 520 + lift);
      ctx.lineTo(x + 50, 320 + lift);
      ctx.closePath();
      ctx.fill();
      // lid
      ctx.fillStyle = C.cream;
      roundRect(ctx, x - 55, 300 + lift, 110, 24, 6);
      ctx.fill();
      // straw
      ctx.fillStyle = colors[i];
      roundRect(ctx, x + 10, 250 + lift, 10, 70, 3);
      ctx.fill();
      ctx.fillStyle = C.cream;
      ctx.font = "700 26px 'Noto Sans SC', sans-serif";
      ctx.textAlign = "center";
      ctx.fillText("卖点 " + String.fromCharCode(65+i), x, 580);
      ctx.fillStyle = colors[i];
      ctx.font = "600 22px 'Noto Sans SC', sans-serif";
      ctx.fillText(lab, x, 620);
      // metric bars
      const h = (0.3 + seeded(i+3)*0.6) * easeOut(frac(local, 2, 4)) * 120;
      ctx.fillStyle = colors[i];
      roundRect(ctx, x - 20, 700 - h, 40, h, 6);
      ctx.fill();
      ctx.globalAlpha = 1;
    });
    ctx.fillStyle = C.mute;
    ctx.font = "600 22px 'Noto Sans SC', sans-serif";
    ctx.textAlign = "center";
    ctx.fillText("在相近投放条件下观察差异（示意）", W/2, 760);
  }

  function sceneClose(ctx, t) {
    // 109.8–118
    const local = t - 109.8;
    const a = easeOut(frac(local, 0, 0.8));
    ctx.globalAlpha = a;
    cameraBody(ctx, W/2, 380, 1.6, Math.sin(local)*0.05);
    ctx.fillStyle = C.cream;
    ctx.font = "800 48px 'Noto Serif SC', serif";
    ctx.textAlign = "center";
    ctx.fillText("先想清商业任务", W/2, 560);
    ctx.fillStyle = C.gold;
    ctx.font = "600 28px 'Noto Sans SC', sans-serif";
    ctx.fillText("再拿起相机", W/2, 620);
    ctx.fillStyle = C.mute;
    ctx.font = "italic 400 22px 'Noto Serif SC', serif";
    ctx.fillText("From shooter to someone who understands the business.", W/2, 680);
    // end mark
    if (local > 4) {
      const e = easeOut(frac(local, 4, 5));
      ctx.globalAlpha = e;
      ctx.fillStyle = C.gold;
      ctx.font = "600 20px 'Noto Sans SC', sans-serif";
      ctx.fillText("VIBE 知识大赏", W/2, 760);
    }
    ctx.globalAlpha = 1;
  }

  // —— master render ——
  function render(ctx, t) {
    t = clamp(t, 0, DURATION);
    bg(ctx, t);
    if (t < 6.4) sceneHook(ctx, t);
    else if (t < 14) sceneTitle(ctx, t);
    else if (t < 21) sceneIndustry(ctx, t);
    else if (t < 36.5) sceneFiveGames(ctx, t);
    else if (t < 49) sceneViewsMoney(ctx, t);
    else if (t < 61.8) sceneBuyReason(ctx, t);
    else if (t < 75) sceneRights(ctx, t);
    else if (t < 88.2) sceneAccess(ctx, t);
    else if (t < 101.2) sceneHourly(ctx, t);
    else if (t < 109.8) sceneHypothesis(ctx, t);
    else sceneClose(ctx, t);

    // title card overlay watermark-free; top label + subs on top
    if (!(t >= 6.4 && t < 14)) topLabel(ctx, t);
    subtitle(ctx, t);
  }

  window.render = render;
})();
