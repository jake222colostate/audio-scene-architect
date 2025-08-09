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
    """Load AudioGen model into GPU memory."""
    global MODEL, HEAVY_READY, LAST_HEAVY_ERROR
    if MODEL is not None:
        HEAVY_READY = True
        return
    name = model_name or os.getenv("AUDIOGEN_MODEL", "facebook/audiogen-medium")
    try:
        import torch
        if not torch.cuda.is_available():
            raise HeavyLoadError("CUDA not available")
        from audiocraft.models import AudioGen
        MODEL = AudioGen.get_pretrained(name).to("cuda")
        HEAVY_READY = True
        LAST_HEAVY_ERROR = None
    except Exception as e:
        LAST_HEAVY_ERROR = str(e)
        HEAVY_READY = False
        raise HeavyLoadError(str(e))


def generate(prompt: str, seconds: int, sr: int = 32000) -> np.ndarray:
    """Generate audio using the heavy model and return a numpy array."""
    global LAST_HEAVY_ERROR
    try:
        import torch, torchaudio
        load_model()
        seconds = max(1, int(seconds))
        MODEL.set_generation_params(duration=seconds, use_sampling=True, top_k=250, top_p=0.0,
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
