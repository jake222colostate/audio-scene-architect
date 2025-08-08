import uuid
from pathlib import Path
import numpy as np
import soundfile as sf

SAMPLE_RATE = 44100


def _fade(signal: np.ndarray, ms: int = 40) -> np.ndarray:
    n = len(signal)
    fl = max(1, int(SAMPLE_RATE * ms / 1000))
    env_in  = np.linspace(0, 1, fl)
    env_out = np.linspace(1, 0, fl)
    y = signal.copy()
    y[:fl]  *= env_in
    y[-fl:] *= env_out
    return y


def _procedural(prompt: str, seconds: int) -> np.ndarray:
    n = seconds * SAMPLE_RATE
    t = np.linspace(0, seconds, n, endpoint=False)
    seed = abs(hash(prompt)) % (2**32)
    rng = np.random.default_rng(seed)
    f = 110 + (seed % 300)  # 110–409 Hz
    pad = (
        0.6*np.sin(2*np.pi*f*t + rng.random()) +
        0.3*np.sin(2*np.pi*0.5*f*t + rng.random()) +
        0.2*np.sin(2*np.pi*2*f*t + rng.random())
    )
    noise = rng.standard_normal(n).astype(np.float32)
    alpha = 0.02 + (seed % 8)/100.0
    filt = np.zeros_like(noise, dtype=np.float32)
    acc = 0.0
    for i in range(n):
        acc = alpha*noise[i] + (1-alpha)*acc
        filt[i] = acc
    y = pad + 0.25*filt
    y = _fade(y / (np.max(np.abs(y)) + 1e-9), ms=40)
    return y.astype(np.float32)


def generate_file(prompt: str, duration: int, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    audio = _procedural(prompt.strip(), duration)
    out_path = output_dir / f"{uuid.uuid4()}.wav"
    sf.write(out_path, audio, SAMPLE_RATE, subtype="PCM_16")
    return out_path
