import { BLOCK_TYPES, createBlock, demoDocument } from "./blocks.js";
import { previewDocumentHTML } from "./render.js";
import { copyText, downloadText, exportH5, exportWechatHTML } from "./export.js";

const state = {
  doc: demoDocument(),
  selectedId: null,
};

const els = {
  add: document.getElementById("block-add"),
  layers: document.getElementById("layers"),
  props: document.getElementById("props-fields"),
  frame: document.getElementById("preview"),
  toast: document.getElementById("toast"),
  metaTitle: document.getElementById("meta-title"),
  metaAuthor: document.getElementById("meta-author"),
};

function toast(msg) {
  els.toast.textContent = msg;
  els.toast.classList.add("show");
  clearTimeout(toast._t);
  toast._t = setTimeout(() => els.toast.classList.remove("show"), 1800);
}

function selected() {
  return state.doc.blocks.find((b) => b.id === state.selectedId) || null;
}

function ensureSelection() {
  if (!state.doc.blocks.some((b) => b.id === state.selectedId)) {
    state.selectedId = state.doc.blocks[0]?.id || null;
  }
}

function refreshPreview() {
  const html = previewDocumentHTML(state.doc);
  els.frame.srcdoc = html;
}

function renderAddButtons() {
  els.add.innerHTML = BLOCK_TYPES.map(
    (t) => `<button type="button" data-add="${t.type}"><b>${t.label}</b><small>${t.desc}</small></button>`
  ).join("");
}

function renderLayers() {
  ensureSelection();
  els.layers.innerHTML = state.doc.blocks
    .map((b, i) => {
      const active = b.id === state.selectedId ? "active" : "";
      const label = BLOCK_TYPES.find((t) => t.type === b.type)?.label || b.type;
      return `<div class="layer ${active}" data-id="${b.id}">
        <div class="layer-head">
          <button type="button" class="ghost layer-title" data-select="${b.id}">${i + 1}. ${label}</button>
          <div class="layer-actions">
            <button type="button" data-up="${b.id}" title="上移">↑</button>
            <button type="button" data-down="${b.id}" title="下移">↓</button>
            <button type="button" class="danger" data-del="${b.id}" title="删除">删</button>
          </div>
        </div>
      </div>`;
    })
    .join("");
}

const FIELD_MAP = {
  hero: [
    ["brand", "品牌"],
    ["title", "主标题"],
    ["subtitle", "副标题"],
    ["bg", "背景色"],
    ["accent", "强调色"],
  ],
  text: [
    ["eyebrow", "眉题"],
    ["title", "标题"],
    ["body", "正文", "textarea"],
  ],
  image: [
    ["url", "图片 URL"],
    ["caption", "说明"],
    ["height", "高度(设计稿)"],
  ],
  bubble: [
    ["title", "标题"],
    ["hint", "提示"],
    ["count", "泡泡数量"],
    ["color", "颜色"],
  ],
  cards: [
    ["leftTitle", "左标题"],
    ["leftBody", "左文案", "textarea"],
    ["rightTitle", "右标题"],
    ["rightBody", "右文案", "textarea"],
  ],
  footer: [
    ["brand", "英文品牌"],
    ["line", "收束句"],
    ["note", "备注"],
  ],
};

function renderProps() {
  const b = selected();
  els.metaTitle.value = state.doc.meta.title;
  els.metaAuthor.value = state.doc.meta.author;
  if (!b) {
    els.props.innerHTML = `<p class="help">先添加一个积木。</p>`;
    return;
  }
  const fields = FIELD_MAP[b.type] || [];
  els.props.innerHTML = fields
    .map(([key, label, kind]) => {
      const val = b[key] ?? "";
      if (kind === "textarea") {
        return `<div class="field"><label>${label}</label><textarea data-key="${key}">${String(val)}</textarea></div>`;
      }
      return `<div class="field"><label>${label}</label><input data-key="${key}" value="${String(val).replaceAll('"', "&quot;")}"></div>`;
    })
    .join("");
}

function paint() {
  renderLayers();
  renderProps();
  refreshPreview();
}

function move(id, dir) {
  const i = state.doc.blocks.findIndex((b) => b.id === id);
  const j = i + dir;
  if (i < 0 || j < 0 || j >= state.doc.blocks.length) return;
  const [item] = state.doc.blocks.splice(i, 1);
  state.doc.blocks.splice(j, 0, item);
  paint();
}

function bind() {
  renderAddButtons();

  els.add.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-add]");
    if (!btn) return;
    const block = createBlock(btn.dataset.add);
    state.doc.blocks.push(block);
    state.selectedId = block.id;
    paint();
  });

  els.layers.addEventListener("click", (e) => {
    const sel = e.target.closest("[data-select]");
    const up = e.target.closest("[data-up]");
    const down = e.target.closest("[data-down]");
    const del = e.target.closest("[data-del]");
    if (sel) {
      state.selectedId = sel.dataset.select;
      paint();
    } else if (up) move(up.dataset.up, -1);
    else if (down) move(down.dataset.down, 1);
    else if (del) {
      state.doc.blocks = state.doc.blocks.filter((b) => b.id !== del.dataset.del);
      paint();
    }
  });

  els.props.addEventListener("input", (e) => {
    const el = e.target.closest("[data-key]");
    const b = selected();
    if (!el || !b) return;
    const key = el.dataset.key;
    let val = el.value;
    if (key === "count" || key === "height") val = Number(val) || 0;
    b[key] = val;
    refreshPreview();
  });

  els.metaTitle.addEventListener("input", () => {
    state.doc.meta.title = els.metaTitle.value;
  });
  els.metaAuthor.addEventListener("input", () => {
    state.doc.meta.author = els.metaAuthor.value;
  });

  document.getElementById("btn-reset").addEventListener("click", () => {
    state.doc = demoDocument();
    state.selectedId = state.doc.blocks[0].id;
    paint();
    toast("已恢复示例文稿");
  });

  document.getElementById("btn-copy-wx").addEventListener("click", async () => {
    const html = exportWechatHTML(state.doc);
    await copyText(html);
    toast("微信 SVG HTML 已复制");
  });

  document.getElementById("btn-dl-wx").addEventListener("click", () => {
    downloadText("wechat-svg-export.html", exportWechatHTML(state.doc));
    toast("已下载微信导出文件");
  });

  document.getElementById("btn-dl-h5").addEventListener("click", () => {
    downloadText("e2-lite-h5.html", exportH5(state.doc));
    toast("已下载独立 H5");
  });

  document.getElementById("btn-copy-h5").addEventListener("click", async () => {
    await copyText(exportH5(state.doc));
    toast("独立 H5 源码已复制");
  });
}

state.selectedId = state.doc.blocks[0].id;
bind();
paint();
