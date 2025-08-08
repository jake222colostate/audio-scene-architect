"""Audio generation service with optional heavy (GPU) path.

This module exposes ``generate_file`` which will use the AudioGen model when
``USE_HEAVY=1`` *and* a CUDA device is available. If the model fails to load or
no GPU is present, the function transparently falls back to the original
procedural synthesiser so that the demo continues to work in CPU-only
environments.
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Optional

import numpy as np
import soundfile as sf


USE_HEAVY = os.getenv("USE_HEAVY", "0") == "1"
SAMPLE_RATE = 44100


def _fade(signal: np.ndarray, ms: int = 40) -> np.ndarray:
    n = len(signal)
    fl = max(1, int(SAMPLE_RATE * ms / 1000))
    env_in = np.linspace(0, 1, fl)
    env_out = np.linspace(1, 0, fl)
    y = signal.copy()
    y[:fl] *= env_in
    y[-fl:] *= env_out
    return y


def _procedural(prompt: str, seconds: int) -> np.ndarray:
    n = seconds * SAMPLE_RATE
    t = np.linspace(0, seconds, n, endpoint=False)
    seed = abs(hash(prompt)) % (2**32)
    rng = np.random.default_rng(seed)
    f = 110 + (seed % 300)
    pad = (
        0.6 * np.sin(2 * np.pi * f * t + rng.random())
        + 0.3 * np.sin(2 * np.pi * 0.5 * f * t + rng.random())
        + 0.2 * np.sin(2 * np.pi * 2 * f * t + rng.random())
    )
    noise = rng.standard_normal(n).astype(np.float32)
    alpha = 0.02 + (seed % 8) / 100.0
    filt = np.zeros_like(noise, dtype=np.float32)
    acc = 0.0
    for i in range(n):
        acc = alpha * noise[i] + (1 - alpha) * acc
        filt[i] = acc
    y = pad + 0.25 * filt
    y = _fade(y / (np.max(np.abs(y)) + 1e-9), ms=40)
    return y.astype(np.float32)


def _try_heavy(
    prompt: str, seconds: int, sample_rate: int, seed: Optional[int] = None
) -> np.ndarray:
    from backend.services import heavy_audiogen

    if not heavy_audiogen.is_available():
        raise RuntimeError("Heavy not available")
    return heavy_audiogen.generate_wav(
        prompt, seconds, sample_rate=sample_rate, seed=seed
    )


def generate_file(
    prompt: str,
    duration: int,
    output_dir: Path,
    sample_rate: int = SAMPLE_RATE,
    seed: Optional[int] = None,
) -> Path:
    """Generate audio and write it to ``output_dir`` as a WAV file."""

    output_dir.mkdir(parents=True, exist_ok=True)
    if USE_HEAVY:
        try:
            audio = _try_heavy(prompt, duration, sample_rate, seed=seed)
        except Exception as e:  # pragma: no cover - logging only
            print(f"[heavy] falling back to procedural: {e}")
            audio = _procedural(prompt, duration)
    else:
        audio = _procedural(prompt, duration)

    out_path = output_dir / f"{uuid.uuid4()}.wav"
    sf.write(out_path, audio, sample_rate, subtype="PCM_16")
    return out_path

