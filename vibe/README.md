# 拍视频赚钱的底层逻辑 · vibe 知识打赏视频

竖屏 9:16 知识分镜，黑底大字 + 中文旁白。

## 在线预览

打开站点 `/vibe/`，点「播放」自动翻页。

## 成品视频

`short-video-money-logic.mp4`（约 4 分钟，可直接发抖音 / 小红书）

## 重新渲染

```bash
pip install edge-tts playwright
python -m playwright install chromium
python3 vibe/render.py
```

依赖本机 `ffmpeg`。文案在 `slides.js`。
