import math
import random
import uuid
from pathlib import Path
import numpy as np
import soundfile as sf

SAMPLE_RATE = 44100

def _fade_in_out(signal: np.ndarray, fade_ms: int = 20) -> np.ndarray:
    n = len(signal)
    fade_len = max(1, int(SAMPLE_RATE * fade_ms / 1000))
    fade_in = np.linspace(0, 1, fade_len)
    fade_out = np.linspace(1, 0, fade_len)
    result = signal.copy()
    result[:fade_len] *= fade_in
    result[-fade_len:] *= fade_out
    return result

def procedural_sfx(prompt: str, seconds: int) -> np.ndarray:
    """
    CPU-safe fallback: synth pads + noise textures that vary with the prompt.
    Not 'realistic', but always produces a pleasant bed suitable for demo.
    """
    duration = seconds
    n = duration * SAMPLE_RATE
    t = np.linspace(0, duration, n, endpoint=False)

    # Map prompt hash to deterministic seeds
    seed = abs(hash(prompt)) % (2**32)
    rng = np.random.default_rng(seed)

    base_freq = 110 + (seed % 400)  # 110–510 Hz
    mod_freq = 0.1 + (seed % 30) / 100.0  # 0.1–0.4 Hz

    # Pad: stacked detuned sines
    pad = (
        0.5 * np.sin(2*np.pi*(base_freq)*t + rng.random()) +
        0.3 * np.sin(2*np.pi*(base_freq*2)*t + rng.random()) +
        0.2 * np.sin(2*np.pi*(base_freq*0.5)*t + rng.random())
    )

    # Slow amplitude modulation
    lfo = (np.sin(2*np.pi*mod_freq*t) + 1) * 0.5
    pad = pad * (0.5 + 0.5*lfo)

    # Texture: filtered noise
    noise = rng.standard_normal(n).astype(np.float32)
    # Simple low-pass via cumulative sum (cheap)
    alpha = 0.01 + (seed % 8)/100.0
    filt = np.zeros_like(noise)
    acc = 0.0
    for i in range(n):
        acc = alpha*noise[i] + (1-alpha)*acc
        filt[i] = acc
    texture = 0.2 * filt

    # Subtle “footstep” pulses if keywords present
    steps = 0
    if any(k in prompt.lower() for k in ["step", "foot", "walk", "crunch", "leaves"]):
        steps = int(duration * 2)
        pulse = np.zeros(n, dtype=np.float32)
        stride = int(SAMPLE_RATE * 0.5)
        for i in range(steps):
            idx = min(i * stride + rng.integers(0, int(0.1*SAMPLE_RATE)), n-1)
            length = int(0.04 * SAMPLE_RATE)
            env = np.hanning(length)
            s = np.zeros(n, dtype=np.float32)
            s[idx:idx+length] = env
            pulse += s * 0.4
        texture += pulse

    signal = pad + texture
    # Normalize
    mx = np.max(np.abs(signal)) + 1e-9
    signal = 0.9 * (signal / mx)
    signal = _fade_in_out(signal, fade_ms=40)
    return signal.astype(np.float32)

def generate_file(prompt: str, duration: int, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    audio = procedural_sfx(prompt, duration)
    file_id = str(uuid.uuid4())
    out_path = output_dir / f"{file_id}.wav"
    sf.write(out_path, audio, SAMPLE_RATE, subtype="PCM_16")
    return out_path
