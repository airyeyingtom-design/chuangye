#!/usr/bin/env python3
"""Synthesize event SFX and mix with BGM for the landscape vibe film."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np
from scipy.io import wavfile

SR = 44100
ROOT = Path(__file__).resolve().parent
AUDIO = ROOT.parent / "audio"
OUT = Path("/tmp/vibe-land/audio")
OUT.mkdir(parents=True, exist_ok=True)


def env(n, a=0.005, d=0.08, s=0.3, r=0.2):
    a_n, d_n, r_n = int(a * SR), int(d * SR), int(r * SR)
    s_n = max(0, n - a_n - d_n - r_n)
    parts = []
    if a_n:
        parts.append(np.linspace(0, 1, a_n, endpoint=False))
    if d_n:
        parts.append(np.linspace(1, s, d_n, endpoint=False))
    parts.append(np.full(s_n, s))
    if r_n:
        parts.append(np.linspace(s, 0, r_n))
    e = np.concatenate(parts) if parts else np.zeros(n)
    if len(e) < n:
        e = np.pad(e, (0, n - len(e)))
    return e[:n]


def make_sfx(name: str) -> np.ndarray:
    rng = np.random.default_rng(abs(hash(name)) % (2**32))
    if name == "whoosh":
        n = int(0.35 * SR)
        t = np.arange(n) / SR
        noise = rng.uniform(-1, 1, n)
        # bandpass-ish via multiply sine sweep
        sweep = np.sin(2 * np.pi * (400 + 2400 * (t / 0.35)) * t)
        return noise * sweep * env(n, 0.02, 0.1, 0.4, 0.2) * 0.35
    if name == "boom":
        n = int(0.45 * SR)
        t = np.arange(n) / SR
        f = 90 * np.exp(-t * 8)
        return np.sin(2 * np.pi * f * t) * env(n, 0.002, 0.12, 0.35, 0.25) * 0.7
    if name == "tick":
        n = int(0.08 * SR)
        t = np.arange(n) / SR
        return np.sin(2 * np.pi * 1800 * t) * np.exp(-t * 60) * 0.35
    if name == "pop":
        n = int(0.12 * SR)
        t = np.arange(n) / SR
        return np.sin(2 * np.pi * 660 * t) * np.exp(-t * 25) * 0.4
    if name == "coin":
        n = int(0.25 * SR)
        t = np.arange(n) / SR
        return (
            np.sin(2 * np.pi * 1200 * t) * np.exp(-t * 12)
            + 0.5 * np.sin(2 * np.pi * 1800 * t) * np.exp(-t * 18)
        ) * 0.3
    if name == "stamp":
        n = int(0.18 * SR)
        t = np.arange(n) / SR
        noise = rng.uniform(-1, 1, n) * np.exp(-t * 30)
        thump = np.sin(2 * np.pi * 140 * t) * np.exp(-t * 20)
        return (noise * 0.4 + thump) * 0.45
    # soft
    n = int(0.2 * SR)
    t = np.arange(n) / SR
    return np.sin(2 * np.pi * 520 * t) * np.exp(-t * 10) * 0.25


def mix(duration: float, events: list[list], bgm_path: Path, out_wav: Path):
    n = int(duration * SR) + SR
    bed = np.zeros(n, dtype=np.float64)
    bgm = wavfile.read(bgm_path)[1].astype(np.float64)
    if bgm.ndim > 1:
        bgm = bgm.mean(axis=1)
    bgm = bgm / (np.max(np.abs(bgm)) + 1e-9) * 0.32
    bed[: min(len(bgm), n)] += bgm[:n]

    for t, name in events:
        s = make_sfx(name)
        i0 = int(float(t) * SR)
        i1 = min(n, i0 + len(s))
        bed[i0:i1] += s[: i1 - i0]

    peak = np.max(np.abs(bed)) + 1e-9
    bed = bed / peak * 0.92
    # soft limiter
    bed = np.tanh(bed * 1.1)
    wavfile.write(out_wav, SR, (bed * 32767).astype(np.int16))
    print("mixed", out_wav)


def events_from_node() -> list:
    # Evaluate film.js SFX via a tiny html-less extract: parse the array literal we know
    # Prefer extracting via playwright later; for now read the hardcoded list by running node with film stub
    script = r"""
    const fs = require('fs');
    const vm = require('vm');
    const code = fs.readFileSync(process.argv[1], 'utf8');
    const ctx = { window: {}, console };
    vm.createContext(ctx);
    vm.runInContext(code, ctx);
    process.stdout.write(JSON.stringify(ctx.window.getSfxEvents()));
    """
    raw = subprocess.check_output(
        ["node", "-e", script, str(ROOT / "film.js")], text=True
    )
    return json.loads(raw)


if __name__ == "__main__":
    events = events_from_node()
    print(len(events), "sfx events")
    bgm = AUDIO / "we_never_style.wav"
    if not bgm.exists():
        mp3 = AUDIO / "we_never_style.mp3"
        tmp = OUT / "bgm.wav"
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(mp3), str(tmp)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        bgm = tmp
    mix(118.0, events, bgm, OUT / "mix.wav")
