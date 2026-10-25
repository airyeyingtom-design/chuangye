#!/usr/bin/env python3
"""Render landscape vibe knowledge film: stills QA → full frames → mux."""
from __future__ import annotations

import asyncio
import shutil
import subprocess
import sys
from pathlib import Path

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent.parent
FRAMES = Path("/tmp/vibe-land/frames")
AUDIO = Path("/tmp/vibe-land/audio/mix.wav")
OUT_MP4 = ROOT / "vibe-knowledge-landscape.mp4"
OUT_ARTIFACT = Path("/opt/cursor/artifacts/vibe-knowledge-landscape.mp4")
STILLS = Path("/opt/cursor/artifacts")
PORT = 8766
W, H = 1920, 1080
FPS = 24
DURATION = 118.0


def run(cmd):
    print("+", " ".join(map(str, cmd)), flush=True)
    subprocess.run(cmd, check=True)


async def prep_page(p):
    browser = await p.chromium.launch(
        headless=True,
        args=["--font-render-hinting=none", "--disable-lcd-text"],
    )
    page = await browser.new_page(
        viewport={"width": W, "height": H},
        device_scale_factor=1,
    )
    await page.goto(f"http://127.0.0.1:{PORT}/vibe/land/", wait_until="networkidle")
    await page.wait_for_function("window.__ready === true")
    await page.wait_for_timeout(400)
    return browser, page


async def capture_stills():
    times = [0.8, 8.0, 16.0, 26.0, 39.0, 52.0, 64.0, 78.0, 92.0, 104.0, 112.0]
    FRAMES.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        browser, page = await prep_page(p)
        for i, t in enumerate(times):
            await page.evaluate("(t) => window.seek(t)", t)
            await page.wait_for_timeout(80)
            path = STILLS / f"vibe-land-still-{i:02d}-{t:.0f}s.png"
            await page.screenshot(path=str(path), full_page=False)
            print("still", path, flush=True)
        await browser.close()


async def capture_all():
    if FRAMES.exists():
        shutil.rmtree(FRAMES)
    FRAMES.mkdir(parents=True)
    n = int(DURATION * FPS)
    async with async_playwright() as p:
        browser, page = await prep_page(p)
        for i in range(n):
            t = i / FPS
            await page.evaluate("(t) => window.seek(t)", t)
            # tiny settle for font/path
            path = FRAMES / f"f{i:05d}.jpg"
            await page.screenshot(path=str(path), type="jpeg", quality=88)
            if i % 48 == 0:
                print(f"frame {i}/{n} t={t:.2f}", flush=True)
        await browser.close()
    print("frames done", n)


def mux():
    run(
        [
            "ffmpeg",
            "-y",
            "-framerate",
            str(FPS),
            "-i",
            str(FRAMES / "f%05d.jpg"),
            "-i",
            str(AUDIO),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-crf",
            "18",
            "-preset",
            "medium",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            "-movflags",
            "+faststart",
            str(OUT_MP4),
        ]
    )
    shutil.copy2(OUT_MP4, OUT_ARTIFACT)
    print("wrote", OUT_MP4)
    print("wrote", OUT_ARTIFACT)


async def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    server = subprocess.Popen(
        ["python3", "-m", "http.server", str(PORT), "--bind", "127.0.0.1"],
        cwd=str(REPO),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        if mode in ("stills", "all"):
            await capture_stills()
        if mode in ("frames", "all"):
            await capture_all()
            mux()
    finally:
        server.terminate()
        server.wait(timeout=5)


if __name__ == "__main__":
    asyncio.run(main())
