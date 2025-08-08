"""GPU-only AudioGen inference helper.

This module wraps the AudioCraft ``AudioGen`` model and exposes a simple
function to generate waveforms on CUDA devices. It is intentionally kept
separate from the lightweight procedural generator so that the project can
run in CPU-only environments without pulling in heavy dependencies.
"""

from typing import Optional

import numpy as np
import torch
import torchaudio
from audiocraft.models import AudioGen


_MODEL: Optional[AudioGen] = None
_DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
_DEFAULT_MODEL = "facebook/audiogen-medium"


def is_available() -> bool:
    """Return ``True`` if CUDA is available and the heavy model can be used."""

    return _DEVICE == "cuda"


def _load_model() -> AudioGen:
    """Lazy-load the AudioGen model on first use."""

    global _MODEL
    if _MODEL is None:
        _MODEL = AudioGen.get_pretrained(_DEFAULT_MODEL).to(_DEVICE)
        # Default duration; callers can override per generation call.
        _MODEL.set_generation_params(duration=5)
    return _MODEL


def generate_wav(
    prompt: str,
    seconds: int,
    sample_rate: int = 44100,
    seed: Optional[int] = None,
) -> np.ndarray:
    """Generate a mono float32 waveform in ``[-1, 1]``.

    Parameters
    ----------
    prompt:
        Text description of the desired audio.
    seconds:
        Duration of the output clip. Values are clamped to ``[1, 30]``.
    sample_rate:
        Target sampling rate for the returned array. AudioGen internally
        operates around ``32 kHz``; resampling is applied if necessary.
    seed:
        Optional manual random seed for reproducibility.
    """

    if not is_available():
        raise RuntimeError("Heavy mode not available (no CUDA)")

    model = _load_model()
    seconds = max(1, min(int(seconds), 30))
    model.set_generation_params(
        duration=seconds,
        use_sampling=True,
        top_k=250,
        top_p=0.0,
        temperature=1.0,
    )
    if seed is not None:
        torch.manual_seed(int(seed))

    wavs = model.generate([prompt])
    wav = wavs[0].detach().cpu()
    if wav.ndim > 1:
        wav = wav.mean(0)

    model_sr = 32000
    if sample_rate != model_sr:
        wav = torchaudio.functional.resample(
            wav, orig_freq=model_sr, new_freq=sample_rate
        )

    wav = torch.clamp(wav, -1.0, 1.0).float().numpy()
    return wav

