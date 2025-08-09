import os
from typing import Optional
import numpy as np

# Lazy imports inside functions for safety on CPU images
_MODEL = None
_LAST_ERROR: Optional[str] = None
_DEFAULT_MODEL = os.getenv("AUDIOGEN_MODEL", "facebook/audiogen-medium")

def last_error() -> Optional[str]:
    return _LAST_ERROR

def _device_ok() -> bool:
    try:
        import torch
        return torch.cuda.is_available()
    except Exception:
        return False

def _load_model():
    global _MODEL, _LAST_ERROR
    if _MODEL is not None:
        return _MODEL
    if not _device_ok():
        _LAST_ERROR = "CUDA not available (torch.cuda.is_available() == False)"
        raise RuntimeError(_LAST_ERROR)
    try:
        import torch
        from audiocraft.models import AudioGen
    except ModuleNotFoundError as e:
        missing = e.name or str(e)
        if missing == "T5EncoderModel" or "T5EncoderModel" in missing:
            _LAST_ERROR = (
                "Missing dependency 'transformers' (T5EncoderModel). "
                "Install heavy requirements: pip install -r backend/requirements-heavy.txt"
            )
        else:
            _LAST_ERROR = f"Missing dependency: {missing}"
        raise RuntimeError(_LAST_ERROR) from e
    try:
        _MODEL = AudioGen.get_pretrained(_DEFAULT_MODEL).to("cuda")
        _MODEL.set_generation_params(
            duration=5, use_sampling=True, top_k=250, top_p=0.0,
            temperature=1.0, cfg_coef=3.5
        )
        _LAST_ERROR = None
        return _MODEL
    except Exception as e:
        _LAST_ERROR = f"Failed to load '{_DEFAULT_MODEL}': {e}"
        raise

def generate_wav(prompt: str, seconds: int, sample_rate: int = 44100, seed: Optional[int] = None) -> np.ndarray:
    """Return mono float32 [-1,1] waveform at sample_rate using AudioGen; raise on failure."""
    global _LAST_ERROR
    _LAST_ERROR = None

    import torch, torchaudio
    model = _load_model()
    seconds = max(1, min(int(seconds), 30))
    model.set_generation_params(
        duration=seconds, use_sampling=True, top_k=250, top_p=0.0,
        temperature=1.0, cfg_coef=3.5
    )
    if seed is not None:
        torch.manual_seed(int(seed))
    try:
        wavs = model.generate([prompt])  # list[Tensor] at ~32kHz
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
