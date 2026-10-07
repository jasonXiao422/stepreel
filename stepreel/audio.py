"""Procedural soundtrack keyed to timeline events (no samples, no licensing issues)."""
import wave

import numpy as np

SR = 44100


def _lowpass(x, fc):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X *= 1 / (1 + (f / fc) ** 4)
    return np.fft.irfft(X, len(x))


def _env(t, t0, a, d, length):
    e = np.zeros_like(t)
    m = (t >= t0) & (t < t0 + length)
    x = t[m] - t0
    e[m] = np.minimum(x / a, 1) * np.exp(-np.maximum(x - a, 0) / d)
    return e


def _whoosh(t, t0, length, rising, rng):
    n = rng.standard_normal(len(t))
    bands = [_lowpass(n, fc) for fc in (300, 1200, 4500)]
    p = np.clip((t - t0) / length, 0, 1)
    p = p if rising else 1 - p
    w = [np.clip(1 - abs(p * 2 - i), 0, 1) for i in range(3)]
    sig = sum(b * wi for b, wi in zip(bands, w))
    return sig / (np.abs(sig).max() + 1e-9) * _env(t, t0, length * 0.6, length * 0.25, length)


def _click(t, t0, f, g, rng):
    return g * _env(t, t0, 0.002, 0.03, 0.15) * (np.sin(2 * np.pi * f * t) + 0.5 * rng.standard_normal(len(t)))


def _thump(t, t0, g):
    x = (t - t0).clip(0)
    return g * _env(t, t0, 0.005, 0.18, 0.6) * np.sin(2 * np.pi * 55 * x * np.exp(-x * 3))


def synth(path, duration, events, music=None, sfx=True, seed=3):
    t = np.arange(int(SR * duration)) / SR
    rng = np.random.default_rng(seed)
    out = np.zeros_like(t)
    if not music:
        for f, g in [(55, .22), (55.4, .18), (82.4, .12), (110, .07), (164.8, .04)]:
            out += g * np.sin(2 * np.pi * f * t + np.sin(2 * np.pi * 0.2 * t))
        out *= np.clip(t / 1.5, 0, 1) * np.clip((duration - t) / 0.8, 0, 1) * 0.55
    if sfx:
        e0, a0, a1 = events["explode_start"], events["assemble_start"], events["assemble_end"]
        out += 0.9 * _whoosh(t, e0, 1.6, True, rng)
        for i, x in enumerate(np.linspace(e0 + 0.05, e0 + 0.3, 6)):
            out += _click(t, x, 2200 + i * 150, 0.18, rng)
        out += 0.8 * _whoosh(t, a0, 1.3, False, rng)
        for i, x in enumerate(np.linspace(a1 - 0.5, a1 - 0.05, 7)):
            out += _click(t, x, 1500 + i * 120, 0.22, rng)
        out += _thump(t, a1 - 0.3, 0.9)
    out = out / (np.abs(out).max() + 1e-9) * 0.85
    pcm = (out * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(np.stack([pcm, pcm], 1).tobytes())
    return path
