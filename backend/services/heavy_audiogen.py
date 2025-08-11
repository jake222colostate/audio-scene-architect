from __future__ import annotations
import os
from typing import Optional
import numpy as np

MODEL = None
HEAVY_READY = False
LAST_HEAVY_ERROR: Optional[str] = None

class HeavyLoadError(RuntimeError):
    pass

def load_model(model_name: str | None = None) -> None:
    """
    Lazy-load AudioCraft AudioGen and prepare generation params.
    """
    global MODEL, HEAVY_READY, LAST_HEAVY_ERROR
    try:
        import torch
        from audiocraft.models import AudioGen

        name = model_name or os.getenv("AUDIOGEN_MODEL", "facebook/audiogen-medium")
        MODEL = AudioGen.get_pretrained(name)
        MODEL.set_generation_params(duration=8)  # sensible default
        if torch.cuda.is_available():
            MODEL = MODEL.cuda()
        HEAVY_READY = True
        LAST_HEAVY_ERROR = None
    except Exception as e:
        MODEL = None
        HEAVY_READY = False
        LAST_HEAVY_ERROR = str(e)
        raise HeavyLoadError(str(e))

def is_ready() -> bool:
    return bool(HEAVY_READY and MODEL is not None)

def generate(prompt: str, seconds: int, sr: int = 44100) -> np.ndarray:
    """
    Generate audio with AudioGen and return a mono numpy array at `sr`.
    """
    global LAST_HEAVY_ERROR
    if not is_ready():
        load_model()
    try:
        import torch
        import torchaudio

        sec = max(1, int(seconds))
        MODEL.set_generation_params(duration=sec, use_sampling=True, top_k=250, top_p=0.0,
                                    temperature=1.0, cfg_coef=3.5)
        wavs = MODEL.generate([prompt])
        wav = wavs[0].detach().cpu()
        if wav.ndim > 1:
            wav = wav.mean(0)
        if sr != 32000:
            wav = torchaudio.functional.resample(wav, orig_freq=32000, new_freq=sr)
        LAST_HEAVY_ERROR = None
        return wav.numpy()
    except Exception as e:
        LAST_HEAVY_ERROR = str(e)
        raise HeavyLoadError(str(e))
