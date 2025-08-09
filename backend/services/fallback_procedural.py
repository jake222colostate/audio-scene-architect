from __future__ import annotations

import uuid
from pathlib import Path
import numpy as np
from pydub import AudioSegment
import soundfile as sf

from backend.utils.io import ensure_dir, uuid_filename


def generate(prompt: str, seconds: int, out_dir: Path, sr: int = 44100) -> Path:
    """Generate a simple deterministic fallback sound and save to WAV."""
    ensure_dir(out_dir)
    n = int(seconds * sr)
    rng = np.random.default_rng(abs(hash(prompt)) % (2**32))
    t = np.linspace(0, seconds, n, endpoint=False)
    tone = np.sin(2 * np.pi * (220 + (abs(hash(prompt)) % 220)) * t)
    noise = rng.normal(scale=0.2, size=n)
    audio = (tone + noise).astype(np.float32)
    tmp_path = out_dir / uuid_filename(".wav")
    # write via soundfile then fade with pydub
    sf.write(tmp_path, audio, sr)
    seg = AudioSegment.from_file(tmp_path, format="wav").fade_in(20).fade_out(50)
    seg.export(tmp_path, format="wav")
    return tmp_path
