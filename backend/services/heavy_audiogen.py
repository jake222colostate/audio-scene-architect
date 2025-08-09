import os
import torch
import numpy as np
from typing import Optional
from audiocraft.models import AudioGen
import torchaudio

_MODEL: Optional[AudioGen] = None
_LAST_ERROR: Optional[str] = None
_DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
_DEFAULT_MODEL = os.getenv("AUDIOGEN_MODEL", "facebook/audiogen-medium")

def last_error() -> Optional[str]:
    return _LAST_ERROR

def is_available() -> bool:
    return _DEVICE == "cuda"

def _load_model() -> AudioGen:
    global _MODEL, _LAST_ERROR
    if _MODEL is not None:
        return _MODEL
    if not is_available():
        _LAST_ERROR = "CUDA not available (torch.cuda.is_available() == False)"
        raise RuntimeError(_LAST_ERROR)
    try:
        _MODEL = AudioGen.get_pretrained(_DEFAULT_MODEL).to(_DEVICE)
        _MODEL.set_generation_params(duration=5, use_sampling=True,
                                     top_k=250, top_p=0.0, temperature=1.0,
                                     cfg_coef=3.5)
        _LAST_ERROR = None
        return _MODEL
    except Exception as e:
        _LAST_ERROR = f"Failed to load '{_DEFAULT_MODEL}': {e}"
        raise

def generate_wav(prompt: str, seconds: int, sample_rate: int = 44100, seed: Optional[int] = None) -> np.ndarray:
    global _LAST_ERROR
    _LAST_ERROR = None
    model = _load_model()
    seconds = max(1, min(int(seconds), 30))
    model.set_generation_params(duration=seconds, use_sampling=True, top_k=250, top_p=0.0,
                                temperature=1.0, cfg_coef=3.5)
    if seed is not None:
        torch.manual_seed(int(seed))
    try:
        wavs = model.generate([prompt])
    except Exception as e:
        _LAST_ERROR = f"Model.generate failed: {e}"
        raise
    wav = wavs[0].detach().cpu()
    if wav.ndim > 1:
        wav = wav.mean(0)
    model_sr = 32000
    if sample_rate != model_sr:
        wav = torchaudio.functional.resample(wav, orig_freq=model_sr, new_freq=sample_rate)
    return torch.clamp(wav, -1.0, 1.0).float().numpy()
