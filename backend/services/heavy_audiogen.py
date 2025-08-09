import os
from typing import Optional
import numpy as np

# Heavy dependencies are optional; import lazily and allow graceful fallback
try:  # pragma: no cover - best effort import
    import torch  # type: ignore
    from audiocraft.models import AudioGen  # type: ignore
    import torchaudio  # type: ignore
    _IMPORT_ERROR = None
except Exception as e:  # pragma: no cover - handled at runtime
    torch = None  # type: ignore
    AudioGen = None  # type: ignore
    torchaudio = None  # type: ignore
    _IMPORT_ERROR = e

# Singletons
_MODEL = None
_DEVICE = "cuda" if torch and torch.cuda.is_available() else "cpu"
_DEFAULT_MODEL = os.getenv("AUDIOGEN_MODEL", "facebook/audiogen-medium")
_LAST_ERROR = None

def last_error() -> Optional[str]:
    return _LAST_ERROR

def is_available() -> bool:
    return torch is not None and _DEVICE == "cuda"

def _load_model() -> AudioGen:
    global _MODEL, _LAST_ERROR
    if _MODEL is not None:
        return _MODEL
    if torch is None or AudioGen is None or torchaudio is None:
        _LAST_ERROR = f"Heavy dependencies missing: {_IMPORT_ERROR}"
        raise RuntimeError(_LAST_ERROR)
    if not is_available():
        _LAST_ERROR = "CUDA not available"
        raise RuntimeError(_LAST_ERROR)
    try:
        _MODEL = AudioGen.get_pretrained(_DEFAULT_MODEL).to(_DEVICE)
        # Set defaults; will be overridden per-call
        _MODEL.set_generation_params(duration=5, use_sampling=True, top_k=250, top_p=0.0,
                                     temperature=1.0, cfg_coef=3.5)
        return _MODEL
    except Exception as e:
        _LAST_ERROR = f"Failed to load model {_DEFAULT_MODEL}: {e}"
        raise

def generate_wav(
    prompt: str,
    seconds: int,
    sample_rate: int = 44100,
    seed: Optional[int] = None,
) -> np.ndarray:
    """
    Generate mono float32 waveform in [-1,1] at `sample_rate` using AudioGen.
    Raises on error; caller decides fallback.
    """
    global _LAST_ERROR
    _LAST_ERROR = None

    model = _load_model()
    seconds = max(1, min(int(seconds), 30))

    # Tune generation params for SFX fidelity
    model.set_generation_params(
        duration=seconds,
        use_sampling=True,
        top_k=250,
        top_p=0.0,
        temperature=1.0,
        cfg_coef=3.5,  # classifier-free guidance; higher → closer to text
    )
    if seed is not None:
        torch.manual_seed(int(seed))

    try:
        wavs = model.generate([prompt])  # returns list[Tensor]
    except Exception as e:
        _LAST_ERROR = f"Model.generate failed: {e}"
        raise

    wav = wavs[0].detach().cpu()  # [T] or [C,T]
    if wav.ndim > 1:
        wav = wav.mean(0)

    model_sr = 32000
    if sample_rate != model_sr:
        wav = torchaudio.functional.resample(wav, orig_freq=model_sr, new_freq=sample_rate)

    return torch.clamp(wav, -1.0, 1.0).float().numpy()
