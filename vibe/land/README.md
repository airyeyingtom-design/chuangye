# VIBE知识大赏 · 拍视频赚钱的底层逻辑（横屏）

规格：1920×1080 · ~2 分钟 · **无旁白** · 双语字幕 · 矢量动画 · BGM + 音效

## 预览

打开 `/vibe/land/`，点击画面播放。

## 成片

`vibe-knowledge-landscape.mp4`

## 重渲

```bash
python3 vibe/land/synth_sfx.py
# 然后用 Playwright 实时录制 + ffmpeg 混音（见仓库近期 render 流程）
python3 vibe/land/render_film.py stills   # 关键帧自查
```

BGM：自合成的 We Never Remix 气质器乐（113 BPM）。公开发布如需正版曲库，请换成剪映/抖音可商用的《We Never (Remix)》或同类开智小曲。
