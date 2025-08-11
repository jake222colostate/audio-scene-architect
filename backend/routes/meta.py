# backend/routes/meta.py
from __future__ import annotations
import json
import os
import platform as pyplat
import time
from pathlib import Path
from typing import Any, Dict
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from backend.services.state import uptime_seconds, RECENT, dir_size_mb
from backend.services import heavy_audiogen as heavy

router = APIRouter()
APP_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = APP_ROOT / "backend" / "output_audio"
FRONTEND_DIST = APP_ROOT / "frontend" / "dist"
BUILD_INFO = FRONTEND_DIST / "build-info.json"


def _try_import(name: str):
    try:
        return __import__(name)
    except Exception:
        return None


def _routes_summary(app) -> int:
    return len(getattr(app.router, "routes", []))


@router.get("/version")
@router.get("/api/version")
async def version(request: Request):
    torch = _try_import("torch")
    torchaudio = _try_import("torchaudio")
    transformers = _try_import("transformers")
    tokenizers = _try_import("tokenizers")
    audiocraft = _try_import("audiocraft")

    cuda_available = bool(getattr(torch, "cuda", None) and torch.cuda.is_available()) if torch else False
    cuda_count = int(torch.cuda.device_count()) if cuda_available else 0
    cuda_name = torch.cuda.get_device_name(0) if cuda_available and cuda_count else None

    build_tag = os.getenv("BUILD_TAG")
    image_tag = os.getenv("IMAGE_TAG")
    git_sha = os.getenv("GIT_SHA")

    frontend_info: Dict[str, Any] = {}
    if BUILD_INFO.exists():
        try:
            frontend_info = json.loads(BUILD_INFO.read_text())
        except Exception:
            frontend_info = {"error": "malformed build-info.json"}

    disk = None
    try:
        usage = os.statvfs(str(OUTPUT_DIR))
        free_bytes = usage.f_bsize * usage.f_bavail
        disk = round(free_bytes / (1024 * 1024 * 1024), 3)
    except Exception:
        disk = None

    return JSONResponse({
        "build": {
            "build_tag": build_tag,
            "git_sha": (git_sha[:7] if git_sha else None),
            "image_tag": image_tag,
        },
        "platform": {
            "python_version": pyplat.python_version(),
            "platform": pyplat.platform(),
        },
        "cuda": {
            "cuda_available": cuda_available,
            "cuda_device_count": cuda_count,
            "cuda_device": cuda_name,
        },
        "versions": {
            "torch_version": getattr(torch, "__version__", None) if torch else None,
            "torchaudio_version": getattr(torchaudio, "__version__", None) if torchaudio else None,
            "transformers_version": getattr(transformers, "__version__", None) if transformers else None,
            "tokenizers_version": getattr(tokenizers, "__version__", None) if tokenizers else None,
            "audiocraft_version": getattr(audiocraft, "__version__", None) if audiocraft else None,
        },
        "heavy": {
            "heavy_loaded": heavy.is_ready(),
            "last_heavy_error": heavy.last_heavy_error(),
            "model_name": heavy.current_model_name(),
            "device": heavy.current_device(),
        },
        "config": {
            "policy_default": "auto",
            "audio_out_dir": str(OUTPUT_DIR),
            "cache_dir": os.getenv("HF_HOME") or os.getenv("TRANSFORMERS_CACHE") or None,
        },
        "frontend": {
            "frontend_dist_present": FRONTEND_DIST.exists(),
            "frontend_build_info": frontend_info,
        },
        "runtime": {
            "uptime_seconds": uptime_seconds(),
            "routes_count": _routes_summary(request.app),
            "disk_free_gb": disk,
            "audio_dir_size_mb": dir_size_mb(OUTPUT_DIR),
        },
        "recent": list(RECENT),
    })


@router.get("/api/debug/routes")
async def debug_routes(request: Request):
    lines = []
    for r in request.app.router.routes:
        methods = ",".join(sorted(getattr(r, "methods", ["GET"])))
        path = getattr(r, "path", "")
        lines.append({"methods": methods, "path": path})
    return {"count": len(lines), "routes": lines}


@router.get("/api/debug/state")
async def debug_state():
    return {
        "heavy_ready": heavy.is_ready(),
        "last_heavy_error": heavy.last_heavy_error(),
        "model_name": heavy.current_model_name(),
        "device": heavy.current_device(),
        "recent_generations": list(RECENT),
    }


@router.post("/api/debug/selftest")
async def debug_selftest():
    import numpy as np
    # 2-second CPU-only compute to simulate heavy path without file IO
    t0 = time.time()
    sr = 22050
    seconds = 2
    t = np.linspace(0, seconds, sr * seconds, endpoint=False)
    y = np.sin(2 * np.pi * 440 * t) + 0.1 * np.random.default_rng(0).standard_normal(t.shape)
    elapsed = int((time.time() - t0) * 1000)
    return {"ok": True, "ms": elapsed, "rms": float(np.sqrt((y**2).mean()))}