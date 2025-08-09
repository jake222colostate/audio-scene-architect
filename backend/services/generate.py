import os, uuid, importlib
import numpy as np, soundfile as sf
from pathlib import Path

def _detect_heavy_capable() -> bool:
    try:
        import torch
        from audiocraft.models import AudioGen
        return torch.cuda.is_available()
    except Exception:
        return False

_use_heavy_env = os.getenv("USE_HEAVY")
if _use_heavy_env in ("0", "1"):
    USE_HEAVY = (_use_heavy_env == "1")
else:
    USE_HEAVY = _detect_heavy_capable()

ALLOW_FALLBACK = (os.getenv("ALLOW_FALLBACK", "").strip() == "1") if USE_HEAVY else True
SAMPLE_RATE = 44100

def _fade(signal: np.ndarray, ms: int = 40) -> np.ndarray:
    n = len(signal); fl = max(1, int(SAMPLE_RATE * ms / 1000))
    env_in = np.linspace(0,1,fl); env_out = np.linspace(1,0,fl)
    y = signal.copy(); y[:fl]*=env_in; y[-fl:]*=env_out; return y

def _procedural(prompt: str, seconds: int) -> np.ndarray:
    n = seconds * SAMPLE_RATE; t = np.linspace(0, seconds, n, endpoint=False)
    seed = abs(hash(prompt)) % (2**32); rng = np.random.default_rng(seed)
    f = 110 + (seed % 300)
    pad = 0.6*np.sin(2*np.pi*f*t + rng.random()) + 0.3*np.sin(2*np.pi*0.5*f*t + rng.random()) + 0.2*np.sin(2*np.pi*2*f*t + rng.random())
    noise = rng.standard_normal(n).astype(np.float32)
    alpha = 0.02 + (seed % 8)/100.0
    filt = np.zeros_like(noise, dtype=np.float32); acc = 0.0
    for i in range(n): acc = alpha*noise[i] + (1-alpha)*acc; filt[i] = acc
    y = pad + 0.25*filt; y = _fade(y/(np.max(np.abs(y))+1e-9), ms=40)
    return y.astype(np.float32)

def _try_heavy(prompt: str, seconds: int, sample_rate: int, seed=None) -> np.ndarray:
    heavy = importlib.import_module("backend.services.heavy_audiogen")
    return heavy.generate_wav(prompt, seconds, sample_rate=sample_rate, seed=seed)

def generate_file(prompt: str, duration: int, output_dir: Path, sample_rate: int = SAMPLE_RATE, seed=None):
    output_dir.mkdir(parents=True, exist_ok=True)
    if USE_HEAVY:
        try:
            audio = _try_heavy(prompt, duration, sample_rate, seed=seed)
            generator = "heavy"
        except Exception as e:
            if not ALLOW_FALLBACK:
                raise RuntimeError(f"Heavy generation failed; fallback disabled: {e}")
            print(f"[generator] heavy failed, using procedural fallback: {e}")
            audio = _procedural(prompt, duration); generator = "procedural"
    else:
        audio = _procedural(prompt, duration); generator = "procedural"

    out_path = output_dir / f"{uuid.uuid4()}.wav"
    sf.write(out_path, audio, sample_rate, subtype="PCM_16")
    return out_path, generator
