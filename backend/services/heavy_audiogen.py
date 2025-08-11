# backend/services/heavy_audiogen.py
from __future__ import annotations
import os
from dataclasses import dataclass
from typing import Optional

_last_error: Optional[str] = None
_model = None
_model_name: Optional[str] = None
_device = "cpu"

@dataclass
class HeavyInfo:
    ready: bool
    last_error: Optional[str]
    model_name: Optional[str]
    device: str


def _try_imports():
    global torch, AudioGen
    try:
        import torch  # type: ignore
        from audiocraft.models import AudioGen  # type: ignore
        return torch, AudioGen
    except Exception as e:  # noqa: BLE001
        return None, None


def is_ready() -> bool:
    return _model is not None


def last_heavy_error() -> Optional[str]:
    return _last_error


def current_device() -> str:
    return _device


def current_model_name() -> Optional[str]:
    return _model_name


def load_model(model_name: str = "facebook/audiogen-medium") -> bool:
    global _model, _last_error, _device, _model_name
    if _model is not None:
        return True
    torch, AudioGen = _try_imports()
    if torch is None or AudioGen is None:
        _last_error = "audiocraft/torch not importable"
        return False
    try:
        cuda = torch.cuda.is_available()
        _device = "cuda" if cuda else "cpu"
        m = AudioGen.get_pretrained(model_name)
        if cuda:
            m = m.to("cuda")
        _model = m
        _model_name = model_name
        _last_error = None
        return True
    except Exception as e:  # noqa: BLE001
        _last_error = str(e)
        _model = None
        return False


def generate(prompt: str, seconds: int, sample_rate: int | None = None) -> tuple[bytes, int]:
    """Generate raw float32 audio bytes and sample_rate.
    Note: We return CPU numpy bytes to avoid torch dependency at call site.
    """
    global _last_error
    if _model is None:
        raise RuntimeError("heavy model not loaded")
    try:
        # defer imports to runtime context
        import torch
        import numpy as np
        _model.set_generation_params(duration=seconds)
        wavs = _model.generate([prompt])  # [B, C, T]
        wav = wavs[0].detach().to("cpu")
        if wav.dim() == 3:
            wav = wav.squeeze(0)
        sr = getattr(_model.compression_model.cfg, "sample_rate", 44100)
        arr = wav.numpy()
        return arr.tobytes(), int(sr)
    except Exception as e:  # noqa: BLE001
        _last_error = str(e)
        raise