/** Preview / H5 HTML renderer */

function esc(s = "") {
  return String(s)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function nl2br(s = "") {
  return esc(s).replaceAll("\n", "<br>");
}

function renderHero(b) {
  return `
  <section class="blk hero" data-reveal style="--accent:${esc(b.accent)};background:${esc(b.bg)}">
    <p class="brand">${esc(b.brand)}</p>
    <h1>${esc(b.title)}</h1>
    <p class="sub">${esc(b.subtitle)}</p>
  </section>`;
}

function renderText(b) {
  return `
  <section class="blk text" data-reveal>
    <p class="eye">${esc(b.eyebrow)}</p>
    <h2>${esc(b.title)}</h2>
    <p class="body">${nl2br(b.body)}</p>
  </section>`;
}

function renderImage(b) {
  return `
  <section class="blk image" data-reveal>
    <div class="pic" style="aspect-ratio:1080/${Number(b.height) || 720}">
      <img src="${esc(b.url)}" alt="${esc(b.caption)}" loading="lazy">
    </div>
    <p class="cap">${esc(b.caption)}</p>
  </section>`;
}

function renderBubble(b) {
  const n = Math.max(12, Math.min(80, Number(b.count) || 36));
  let cells = "";
  for (let i = 0; i < n; i++) {
    cells += `<button class="bubble" type="button" aria-label="bubble" style="--c:${esc(b.color)}"></button>`;
  }
  return `
  <section class="blk bubble-wrap" data-reveal>
    <h2>${esc(b.title)}</h2>
    <p class="hint">${esc(b.hint)}</p>
    <div class="sheet" data-bubbles>${cells}</div>
  </section>`;
}

function renderCards(b) {
  return `
  <section class="blk cards" data-reveal>
    <article><h3>${esc(b.leftTitle)}</h3><p>${nl2br(b.leftBody)}</p></article>
    <article><h3>${esc(b.rightTitle)}</h3><p>${nl2br(b.rightBody)}</p></article>
  </section>`;
}

function renderFooter(b) {
  return `
  <section class="blk footer" data-reveal>
    <p class="en">${esc(b.brand)}</p>
    <h2>${esc(b.line)}</h2>
    <p class="note">${esc(b.note)}</p>
  </section>`;
}

const RENDERERS = {
  hero: renderHero,
  text: renderText,
  image: renderImage,
  bubble: renderBubble,
  cards: renderCards,
  footer: renderFooter,
};

export function renderBlock(block) {
  const fn = RENDERERS[block.type];
  return fn ? fn(block) : "";
}

export function previewDocumentHTML(doc) {
  const body = doc.blocks.map(renderBlock).join("\n");
  return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>${esc(doc.meta.title)}</title>
<style>
:root{--bg:#0b1016;--paper:#f4efe6;--muted:#9aa6b5;--accent:#6ee0b0;--line:rgba(244,239,230,.12)}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:"PingFang SC","Noto Sans SC",sans-serif;background:var(--bg);color:var(--paper);line-height:1.55}
.blk{padding:28px 20px;border-bottom:1px solid var(--line)}
.hero{min-height:72vh;display:flex;flex-direction:column;justify-content:flex-end;gap:12px}
.hero .brand{letter-spacing:.2em;font-size:12px;color:var(--accent)}
.hero h1{font-size:40px;line-height:1.2;font-weight:700}
.hero .sub,.text .body,.cap,.hint,.note{color:var(--muted)}
.text .eye{font-size:11px;letter-spacing:.24em;color:var(--accent);margin-bottom:10px}
.text h2,.footer h2,.bubble-wrap h2{font-size:28px;line-height:1.3;margin-bottom:12px}
.pic{overflow:hidden;border-radius:4px;background:#111}
.pic img{width:100%;height:100%;object-fit:cover;display:block}
.cap{margin-top:8px;font-size:12px}
.sheet{display:grid;grid-template-columns:repeat(6,1fr);gap:8px;margin-top:16px}
.bubble{aspect-ratio:1;border:0;border-radius:50%;background:radial-gradient(circle at 35% 30%,#fff8,#0000 40%),var(--c,#7ec9ff);opacity:.9;box-shadow:inset -4px -6px 10px rgba(0,0,0,.18),inset 3px 3px 8px rgba(255,255,255,.55)}
.bubble.pop{animation:pop .35s ease forwards;pointer-events:none}
@keyframes pop{to{transform:scale(1.4);opacity:0}}
.cards{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.cards article{border:1px solid var(--line);padding:16px;background:#121821;border-radius:8px}
.cards h3{margin-bottom:8px;font-size:18px}
.cards p{color:var(--muted);font-size:13px;white-space:pre-line}
.footer .en{letter-spacing:.22em;font-size:11px;color:var(--accent);margin-bottom:10px}
.footer .note{margin-top:14px;font-size:11px}
[data-reveal]{opacity:0;transform:translateY(18px);transition:opacity .7s ease,transform .7s ease}
[data-reveal].in{opacity:1;transform:none}
</style>
</head>
<body>
${body}
<script>
document.querySelectorAll('[data-bubbles]').forEach(sheet=>{
  sheet.addEventListener('click',e=>{
    const b=e.target.closest('.bubble');
    if(!b||b.classList.contains('pop'))return;
    b.classList.add('pop');
  });
});
const io=new IntersectionObserver(entries=>{
  entries.forEach(en=>{ if(en.isIntersecting){ en.target.classList.add('in'); io.unobserve(en.target);} });
},{threshold:0.2});
document.querySelectorAll('[data-reveal]').forEach(el=>io.observe(el));
</script>
</body>
</html>`;
}
