from __future__ import annotations
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
    out_path = out_dir / uuid_filename(".wav")
    sf.write(out_path, audio, sr)
    seg = AudioSegment.from_file(out_path, format="wav").fade_in(20).fade_out(50)
    seg.export(out_path, format="wav")
    return out_path
