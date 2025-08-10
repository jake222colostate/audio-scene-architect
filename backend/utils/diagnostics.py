from __future__ import annotations
import os, platform, subprocess, time
from pathlib import Path
from typing import Any, Dict
from .io import disk_free_gb, get_dir_size_mb

def _git_sha() -> str | None:
    try:
        return subprocess.check_output(["git","rev-parse","--short","HEAD"], text=True).strip()
    except Exception:
        return None

def gather_version_payload(app) -> Dict[str, Any]:
    audio_dir = Path(getattr(app.state, "audio_out_dir", Path("backend/output_audio")))
    try: import torch
    except Exception: torch = None
    try: import torchaudio
    except Exception: torchaudio = None
    try: import transformers
    except Exception: transformers = None
    try: import tokenizers
    except Exception: tokenizers = None
    try: import audiocraft
    except Exception: audiocraft = None

    heavy_loaded = getattr(app.state, "heavy_loaded", False)
    last_heavy_error = getattr(app.state, "last_heavy_error", None)
    return {
        "build_tag": os.getenv("BUILD_TAG", "dev"),
        "git_sha": _git_sha(),
        "image_tag": os.getenv("IMAGE_TAG"),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "cuda_available": bool(torch and torch.cuda.is_available()),
        "cuda_device_count": int(torch.cuda.device_count()) if torch and torch.cuda.is_available() else 0,
        "cuda_device": (torch.cuda.get_device_name(0) if torch and torch.cuda.is_available() and torch.cuda.device_count() > 0 else None),
        "torch_version": getattr(torch, "__version__", None),
        "torchaudio_version": getattr(torchaudio, "__version__", None),
        "transformers_version": getattr(transformers, "__version__", None),
        "tokenizers_version": getattr(tokenizers, "__version__", None),
        "audiocraft_version": getattr(audiocraft, "__version__", None),
        "use_heavy_env": os.getenv("USE_HEAVY"),
        "allow_fallback": os.getenv("ALLOW_FALLBACK"),
        "audiogen_model": os.getenv("AUDIOGEN_MODEL", "facebook/audiogen-medium"),
        "audio_out_dir": str(audio_dir),
        "public_base_url": os.getenv("PUBLIC_BASE_URL"),
        "last_heavy_error": last_heavy_error,
        "heavy_loaded": bool(heavy_loaded),
        "uptime_seconds": int(time.time() - app.state.start_time),
        "routes_count": len(app.router.routes),
        "disk_free_gb": disk_free_gb(audio_dir),
        "audio_dir_size_mb": get_dir_size_mb(audio_dir),
        "recent_generations": list(getattr(app.state, "recent_generations", [])),
    }
