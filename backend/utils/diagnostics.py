from __future__ import annotations

import os
import platform
import subprocess
import time
from pathlib import Path
from typing import Any, Dict

from .io import disk_free_gb, get_dir_size_mb


def get_git_sha() -> str | None:
    try:
        return subprocess.check_output([
            "git", "rev-parse", "--short", "HEAD"
        ], text=True).strip()
    except Exception:
        return None


def gather_version_payload(app) -> Dict[str, Any]:
    """Collect diagnostic information for /version and /debug/state."""
    python_version = platform.python_version()
    platform_name = platform.platform()

    cuda_available = False
    cuda_device_count = 0
    cuda_device = None
    torch_version = torchaudio_version = transformers_version = tokenizers_version = audiocraft_version = None
    torch_cuda_runtime = cudnn_version = None

    try:
        import torch
        cuda_available = torch.cuda.is_available()
        cuda_device_count = torch.cuda.device_count()
        if cuda_available and cuda_device_count > 0:
            cuda_device = torch.cuda.get_device_name(0)
            try:
                cudnn_version = torch.backends.cudnn.version()
            except Exception:
                cudnn_version = None
            torch_cuda_runtime = torch.version.cuda
        torch_version = torch.__version__
    except Exception:
        pass

    try:
        import torchaudio
        torchaudio_version = torchaudio.__version__
    except Exception:
        pass

    try:
        import transformers
        transformers_version = transformers.__version__
    except Exception:
        pass

    try:
        import tokenizers
        tokenizers_version = tokenizers.__version__
    except Exception:
        pass

    try:
        import audiocraft
        audiocraft_version = audiocraft.__version__
    except Exception:
        pass

    audio_dir = Path(app.state.audio_out_dir)
    payload: Dict[str, Any] = {
        "build_tag": os.getenv("BUILD_TAG", "dev"),
        "git_sha": get_git_sha(),
        "image_tag": os.getenv("IMAGE_TAG"),
        "python_version": python_version,
        "platform": platform_name,
        "cuda_available": cuda_available,
        "cuda_device_count": cuda_device_count,
        "cuda_device": cuda_device,
        "torch_version": torch_version,
        "torchaudio_version": torchaudio_version,
        "transformers_version": transformers_version,
        "tokenizers_version": tokenizers_version,
        "audiocraft_version": audiocraft_version,
        "torch_cuda_runtime": torch_cuda_runtime,
        "cudnn_version": cudnn_version,
        "use_heavy_env": os.getenv("USE_HEAVY"),
        "allow_fallback": os.getenv("ALLOW_FALLBACK"),
        "audiogen_model": os.getenv("AUDIOGEN_MODEL", "facebook/audiogen-medium"),
        "audio_out_dir": str(audio_dir),
        "public_base_url": os.getenv("PUBLIC_BASE_URL"),
        "last_heavy_error": getattr(app.state, "last_heavy_error", None),
        "heavy_loaded": getattr(app.state, "heavy_loaded", False),
        "uptime_seconds": int(time.time() - app.state.start_time),
        "routes_count": len(app.router.routes),
        "disk_free_gb": disk_free_gb(audio_dir),
        "audio_dir_size_mb": get_dir_size_mb(audio_dir),
        "recent_generations": list(getattr(app.state, "recent_generations", [])),
    }
    return payload
