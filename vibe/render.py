#!/usr/bin/env python3
"""Render the vibe knowledge tip video as 9:16 MP4 with Chinese TTS."""
from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WORK = Path("/tmp/vibe-render")
FRAMES = WORK / "frames"
AUDIO = WORK / "audio"
CLIPS = WORK / "clips"
OUT_REPO = ROOT / "short-video-money-logic.mp4"
OUT_ARTIFACT = Path("/opt/cursor/artifacts/short-video-money-logic.mp4")
PORT = 8765
W, H = 1080, 1920

# Load slide voices from slides.js without a JS engine: extract the voice fields via a tiny node helper.
SLIDES_JS = ROOT / "slides.js"


def run(cmd: list[str], **kw):
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, **kw)


def load_slides() -> list[dict]:
    # Evaluate slides.js in node and dump JSON
    script = r"""
    const fs = require('fs');
    const vm = require('vm');
    const code = fs.readFileSync(process.argv[1], 'utf8');
    const ctx = { window: {}, console };
    vm.createContext(ctx);
    vm.runInContext(code, ctx);
    process.stdout.write(JSON.stringify(ctx.window.VIBE_SLIDES));
    """
    raw = subprocess.check_output(["node", "-e", script, str(SLIDES_JS)], text=True)
    return json.loads(raw)


async def synth_voices(slides: list[dict]):
    import edge_tts

    AUDIO.mkdir(parents=True, exist_ok=True)
    voice = "zh-CN-YunxiNeural"  # calm, clear male — knowledge tip feel
    paths = []
    for i, s in enumerate(slides):
        text = s.get("voice") or "。".join(s.get("lines", []))
        out = AUDIO / f"{i:02d}.mp3"
        print(f"TTS {i+1}/{len(slides)}: {text[:40]}...", flush=True)
        communicate = edge_tts.Communicate(text, voice, rate="-8%", pitch="-2Hz")
        await communicate.save(str(out))
        paths.append(out)
    return paths


def ffprobe_duration(path: Path) -> float:
    out = subprocess.check_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        text=True,
    ).strip()
    return float(out)


def start_server():
    return subprocess.Popen(
        ["python3", "-m", "http.server", str(PORT), "--bind", "127.0.0.1"],
        cwd=str(ROOT.parent),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


async def capture_frames(n: int):
    from playwright.async_api import async_playwright

    FRAMES.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--font-render-hinting=none", "--disable-lcd-text"],
        )
        page = await browser.new_page(
            viewport={"width": W, "height": H},
            device_scale_factor=1,
        )
        url = f"http://127.0.0.1:{PORT}/vibe/?export=1"
        await page.goto(url, wait_until="networkidle")
        # Wait for web fonts
        await page.wait_for_function("window.__vibe && window.__vibe.ready")
        await page.wait_for_timeout(1200)
        for i in range(n):
            await page.evaluate("(n) => window.__vibe.go(n)", i)
            await page.wait_for_timeout(450)
            path = FRAMES / f"{i:02d}.png"
            await page.screenshot(path=str(path), full_page=False)
            print(f"frame {i+1}/{n} -> {path}", flush=True)
        await browser.close()


def build_video(slides: list[dict], audios: list[Path]):
    CLIPS.mkdir(parents=True, exist_ok=True)
    list_file = WORK / "concat.txt"
    lines = []
    for i, audio in enumerate(audios):
        dur = ffprobe_duration(audio) + 0.35  # short pause between beats
        frame = FRAMES / f"{i:02d}.png"
        clip = CLIPS / f"{i:02d}.mp4"
        fade_out_start = max(dur - 0.35, 0)
        run(
            [
                "ffmpeg",
                "-y",
                "-loop",
                "1",
                "-i",
                str(frame),
                "-i",
                str(audio),
                "-c:v",
                "libx264",
                "-tune",
                "stillimage",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-t",
                f"{dur:.3f}",
                "-vf",
                f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,fade=t=in:st=0:d=0.25,fade=t=out:st={fade_out_start:.3f}:d=0.3",
                "-af",
                f"afade=t=in:st=0:d=0.1,afade=t=out:st={max(dur-0.4,0):.3f}:d=0.35",
                "-shortest",
                str(clip),
            ]
        )
        lines.append(f"file '{clip}'")

    list_file.write_text("\n".join(lines) + "\n")
    draft = WORK / "draft.mp4"
    run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_file),
            "-c",
            "copy",
            str(draft),
        ]
    )

    # Soft low ambient bed under narration (gentle sine pad via ffmpeg lavfi)
    final_tmp = WORK / "final.mp4"
    run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(draft),
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=110:sample_rate=44100",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=164.81:sample_rate=44100",
            "-filter_complex",
            "[1:a]volume=0.015[a1];[2:a]volume=0.01[a2];[a1][a2]amix=inputs=2:duration=longest[bed];[0:a][bed]amix=inputs=2:duration=first:dropout_transition=2[aout]",
            "-map",
            "0:v",
            "-map",
            "[aout]",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            "-movflags",
            "+faststart",
            str(final_tmp),
        ]
    )
    OUT_ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(final_tmp, OUT_REPO)
    shutil.copy2(final_tmp, OUT_ARTIFACT)
    print(f"Wrote {OUT_REPO}", flush=True)
    print(f"Wrote {OUT_ARTIFACT}", flush=True)


async def main():
    if WORK.exists():
        shutil.rmtree(WORK)
    WORK.mkdir(parents=True)

    slides = load_slides()
    print(f"{len(slides)} slides", flush=True)

    server = start_server()
    try:
        audios = await synth_voices(slides)
        await capture_frames(len(slides))
        build_video(slides, audios)
    finally:
        server.terminate()
        server.wait(timeout=5)


if __name__ == "__main__":
    asyncio.run(main())
