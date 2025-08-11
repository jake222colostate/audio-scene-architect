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
    sentencepiece = _try_import("sentencepiece")
    audiocraft = _try_import("audiocraft")

    cuda_available = bool(getattr(torch, "cuda", None) and torch.cuda.is_available()) if torch else False
    cuda_count = int(torch.cuda.device_count()) if cuda_available else 0
    cuda_name = torch.cuda.get_device_name(0) if cuda_available and cuda_count else None
    cuda_runtime = getattr(getattr(torch, "version", None), "cuda", None) if torch else None

    build_tag = os.getenv("BUILD_TAG")
    image_tag = os.getenv("IMAGE_TAG")
    git_sha = os.getenv("GIT_SHA")
    use_heavy = os.getenv("USE_HEAVY", "0")
    allow_fallback = os.getenv("ALLOW_FALLBACK", "1")

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

    # Retrieve last error lazily to avoid circular import
    try:
        from backend import main as _main  # type: ignore
        last_error = getattr(_main, "get_last_error", lambda: {"msg": None, "trace": None})()
    except Exception:
        last_error = {"msg": None, "trace": None}

    libs = {
        "torch": getattr(torch, "__version__", None) if torch else None,
        "torchaudio": getattr(torchaudio, "__version__", None) if torchaudio else None,
        "transformers": getattr(transformers, "__version__", None) if transformers else None,
        "tokenizers": getattr(tokenizers, "__version__", None) if tokenizers else None,
        "sentencepiece": getattr(sentencepiece, "__version__", None) if sentencepiece else None,
        "audiocraft": getattr(audiocraft, "__version__", None) if audiocraft else None,
        "cuda_runtime": cuda_runtime,
    }

    return JSONResponse({
        "build": {
            "build_tag": build_tag,
            "git_sha": (git_sha[:7] if git_sha else None),
            "image_tag": image_tag,
        },
        "build_tag": build_tag,
        "use_heavy": use_heavy,
        "allow_fallback": allow_fallback,
        "platform": {
            "python_version": pyplat.python_version(),
            "platform": pyplat.platform(),
        },
        "cuda": {
            "cuda_available": cuda_available,
            "cuda_device_count": cuda_count,
            "cuda_device": cuda_name,
        },
        "libs": libs,
        "heavy": {
            "heavy_loaded": heavy.is_ready(),
            "last_heavy_error": heavy.last_heavy_error(),
            "model_name": heavy.current_model_name(),
            "device": heavy.current_device(),
        },
        "last_error": last_error,
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


@router.get("/api/diag/verify-heavy")
async def verify_heavy():
    try:
        ok = heavy.load_model()
        if not ok:
            raise RuntimeError(f"load_model failed: {heavy.last_heavy_error()}")
        data, sr = heavy.generate("creepy mechanical hallway", 1)
        return {
            "ok": True,
            "sample_rate": sr,
            "bytes": len(data),
            "device": heavy.current_device(),
            "model": heavy.current_model_name(),
        }
    except Exception as e:
        import traceback
        return JSONResponse(
            status_code=500,
            content={
                "ok": False,
                "error": str(e),
                "last_heavy_error": heavy.last_heavy_error(),
                "trace": traceback.format_exc(),
                "device": heavy.current_device(),
                "model": heavy.current_model_name(),
            },
        )