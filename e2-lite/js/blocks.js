/** Block type definitions and factories for E2-lite */

export const BLOCK_TYPES = [
  { type: "hero", label: "封面 Hero", desc: "大标题 + 背景" },
  { type: "text", label: "滚动文案", desc: "下滑渐入" },
  { type: "image", label: "大图", desc: "全宽配图" },
  { type: "bubble", label: "捏泡泡", desc: "可点击互动" },
  { type: "cards", label: "活动卡", desc: "两列信息" },
  { type: "footer", label: "收尾", desc: "品牌落款" },
];

let _id = 1;
export function uid(prefix = "b") {
  return `${prefix}_${Date.now().toString(36)}_${_id++}`;
}

export function createBlock(type) {
  const id = uid(type);
  switch (type) {
    case "hero":
      return {
        id,
        type,
        title: "你无不无聊？",
        subtitle: "送你一张泡泡纸，无聊就捏着玩吧~",
        brand: "滨江开元广场",
        bg: "#101820",
        accent: "#6ee0b0",
      };
    case "text":
      return {
        id,
        type,
        eyebrow: "WEEKEND",
        title: "这个周末，快乐有点具体",
        body: "有猫、有新店、有福利。往下滑动，把无聊捏碎。",
      };
    case "image":
      return {
        id,
        type,
        url: "https://images.unsplash.com/photo-1574158622682-e40e69881006?w=1080&q=80",
        caption: "本周活动氛围图",
        height: 720,
      };
    case "bubble":
      return {
        id,
        type,
        title: "无聊就来捏泡泡",
        hint: "点一下，破一下",
        count: 36,
        color: "#7ec9ff",
      };
    case "cards":
      return {
        id,
        type,
        leftTitle: "猫展",
        leftBody: "WCF 布兰德杯\n10.17–10.18",
        rightTitle: "新店",
        rightBody: "每味鱼 / 潮头哥\n开业尝鲜",
      };
    case "footer":
      return {
        id,
        type,
        brand: "BINJIANG KAIYUAN PLAZA",
        line: "美好生活，就在开元广场",
        note: "由 E2-lite 导出 · 可用于公众号原文链接或正文粘贴",
      };
    default:
      throw new Error(`Unknown block type: ${type}`);
  }
}

export function demoDocument() {
  return {
    meta: {
      title: "🫧你无不无聊？",
      author: "滨江开元广场",
      width: 1080,
    },
    blocks: [
      createBlock("hero"),
      createBlock("text"),
      createBlock("bubble"),
      createBlock("cards"),
      createBlock("image"),
      createBlock("footer"),
    ],
  };
}
