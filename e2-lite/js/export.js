/** Export WeChat-pasteable SVG sections (E2-style approach, simplified). */

import { previewDocumentHTML } from "./render.js";

function esc(s = "") {
  return String(s)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function nl2br(s = "") {
  return esc(s).replaceAll("\n", "<br/>");
}

/**
 * One WeChat section: SVG shell + foreignObject XHTML (common "黑科技" pattern).
 * Height is in the 1080-wide design coordinate.
 */
function svgSection({ height, inner, label = "e2-lite" }) {
  const h = Math.max(200, Number(height) || 600);
  return `<section style="overflow:hidden;text-align:center;line-height:0;margin:0 auto;-webkit-touch-callout:none;" powered-by="e2-lite" label="${esc(label)}">
<svg viewBox="0 0 1080 ${h}" style="width:100%;max-width:100%;display:block;background:#0b1016;" xmlns="http://www.w3.org/2000/svg">
  <foreignObject x="0" y="0" width="1080" height="${h}">
    <div xmlns="http://www.w3.org/1999/xhtml" style="width:1080px;height:${h}px;margin:0;padding:0;font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Helvetica Neue',sans-serif;color:#f4efe6;background:#0b1016;overflow:hidden;">
      ${inner}
    </div>
  </foreignObject>
</svg>
</section>`;
}

function blockToWechat(block) {
  switch (block.type) {
    case "hero":
      return svgSection({
        label: "hero",
        height: 1100,
        inner: `
          <div style="box-sizing:border-box;height:100%;padding:80px 64px 72px;display:flex;flex-direction:column;justify-content:flex-end;background:linear-gradient(180deg,#15202b 0%,#0b1016 100%);">
            <div style="font-size:28px;letter-spacing:0.28em;color:${esc(block.accent)};margin-bottom:28px;">${esc(block.brand)}</div>
            <div style="font-size:88px;line-height:1.18;font-weight:700;margin-bottom:28px;">${esc(block.title)}</div>
            <div style="font-size:34px;line-height:1.55;color:#9aa6b5;">${esc(block.subtitle)}</div>
          </div>`,
      });
    case "text":
      return svgSection({
        label: "text",
        height: 720,
        inner: `
          <div style="box-sizing:border-box;height:100%;padding:72px 64px;">
            <div style="font-size:26px;letter-spacing:0.28em;color:#6ee0b0;margin-bottom:24px;">${esc(block.eyebrow)}</div>
            <div style="font-size:64px;line-height:1.3;font-weight:700;margin-bottom:28px;">${esc(block.title)}</div>
            <div style="font-size:34px;line-height:1.7;color:#9aa6b5;">${nl2br(block.body)}</div>
          </div>`,
      });
    case "image":
      return svgSection({
        label: "image",
        height: Number(block.height) || 720,
        inner: `
          <div style="box-sizing:border-box;height:100%;padding:24px 32px 40px;">
            <img src="${esc(block.url)}" style="width:100%;height:${(Number(block.height) || 720) - 120}px;object-fit:cover;display:block;border-radius:8px;"/>
            <div style="margin-top:18px;font-size:26px;color:#9aa6b5;text-align:left;">${esc(block.caption)}</div>
          </div>`,
      });
    case "bubble": {
      const n = Math.max(12, Math.min(48, Number(block.count) || 36));
      let cells = "";
      for (let i = 0; i < n; i++) {
        cells += `<div style="width:140px;height:140px;border-radius:50%;background:radial-gradient(circle at 35% 30%,rgba(255,255,255,.55),transparent 42%),${esc(block.color)};box-shadow:inset -6px -8px 14px rgba(0,0,0,.2),inset 4px 4px 10px rgba(255,255,255,.45);display:inline-block;margin:10px;"></div>`;
      }
      return svgSection({
        label: "bubble-static",
        height: 980,
        inner: `
          <div style="box-sizing:border-box;height:100%;padding:56px 48px;">
            <div style="font-size:56px;font-weight:700;margin-bottom:16px;">${esc(block.title)}</div>
            <div style="font-size:30px;color:#9aa6b5;margin-bottom:28px;">${esc(block.hint)}（微信正文内为展示版；完整可捏互动请用独立 H5）</div>
            <div style="text-align:center;line-height:0;">${cells}</div>
          </div>`,
      });
    }
    case "cards":
      return svgSection({
        label: "cards",
        height: 620,
        inner: `
          <div style="box-sizing:border-box;height:100%;padding:48px 40px;display:flex;gap:24px;">
            <div style="flex:1;border:1px solid rgba(244,239,230,.14);border-radius:16px;padding:36px 28px;background:#121821;">
              <div style="font-size:44px;font-weight:700;margin-bottom:18px;">${esc(block.leftTitle)}</div>
              <div style="font-size:30px;line-height:1.6;color:#9aa6b5;">${nl2br(block.leftBody)}</div>
            </div>
            <div style="flex:1;border:1px solid rgba(244,239,230,.14);border-radius:16px;padding:36px 28px;background:#121821;">
              <div style="font-size:44px;font-weight:700;margin-bottom:18px;">${esc(block.rightTitle)}</div>
              <div style="font-size:30px;line-height:1.6;color:#9aa6b5;">${nl2br(block.rightBody)}</div>
            </div>
          </div>`,
      });
    case "footer":
      return svgSection({
        label: "footer",
        height: 700,
        inner: `
          <div style="box-sizing:border-box;height:100%;padding:80px 64px;display:flex;flex-direction:column;justify-content:center;">
            <div style="font-size:26px;letter-spacing:0.28em;color:#6ee0b0;margin-bottom:24px;">${esc(block.brand)}</div>
            <div style="font-size:64px;line-height:1.3;font-weight:700;margin-bottom:24px;">${esc(block.line)}</div>
            <div style="font-size:26px;color:#9aa6b5;">${esc(block.note)}</div>
          </div>`,
      });
    default:
      return "";
  }
}

export function exportWechatHTML(doc) {
  const parts = doc.blocks.map(blockToWechat).filter(Boolean);
  return `<!-- E2-lite export · ${esc(doc.meta.title)} · ${esc(doc.meta.author)} -->
<section style="max-width:100%;margin:0 auto;overflow:hidden;">
${parts.join("\n")}
</section>
<!--
粘贴说明：
1) 电脑 Chrome 打开公众号后台 → 新建图文
2) 推荐用「135 / 秀米 / E2」等编辑器的 HTML 模式粘贴；或开发者工具注入到 #js_content（有失败风险）
3) 捏泡泡等完整互动，请用「导出独立 H5」部署后挂原文链接（最稳）
-->`;
}

export function exportH5(doc) {
  return previewDocumentHTML(doc);
}

export async function copyText(text) {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text);
    return;
  }
  const ta = document.createElement("textarea");
  ta.value = text;
  document.body.appendChild(ta);
  ta.select();
  document.execCommand("copy");
  ta.remove();
}

export function downloadText(filename, text) {
  const blob = new Blob([text], { type: "text/html;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
