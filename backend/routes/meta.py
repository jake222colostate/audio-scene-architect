from fastapi import APIRouter
from fastapi.responses import JSONResponse
import os, sys, platform, importlib
from backend.services.generate import _detect_heavy_capable

router = APIRouter()
app = None  # will be injected by main

@router.get("/health", tags=["meta"])
def health():
    return {"ok": True, "build": os.getenv("BUILD_TAG", "dev")}

@router.get("/version", tags=["meta"])
def version():
    cuda_ok = cuda_ver = dev = None
    try:
        import torch
        cuda_ok = torch.cuda.is_available()
        cuda_ver = getattr(torch.version, "cuda", None)
        dev = torch.cuda.get_device_name(0) if cuda_ok else None
    except Exception:
        pass

    last = None
    tf_ver = tok_ver = None
    try:
        import transformers, tokenizers
        tf_ver = transformers.__version__
        tok_ver = tokenizers.__version__
    except Exception:
        pass
    try:
        heavy = importlib.import_module("backend.services.heavy_audiogen")
        last = getattr(heavy, "last_error")()
    except Exception:
        pass

    return JSONResponse({
        "python": sys.version,
        "platform": platform.platform(),
        "build": os.getenv("BUILD_TAG","dev"),
        "use_heavy_env": os.getenv("USE_HEAVY","0"),
        "allow_fallback": os.getenv("ALLOW_FALLBACK",""),
        "audiogen_model": os.getenv("AUDIOGEN_MODEL","facebook/audiogen-medium"),
        "cuda_available": cuda_ok,
        "cuda_version": cuda_ver,
        "device_name": dev,
        "last_heavy_error": last,
        "detected_heavy_capable": _detect_heavy_capable(),
        "transformers_version": tf_ver,
        "tokenizers_version": tok_ver
    })

@router.get("/debug/state", tags=["debug"])
def debug_state():
    info = {
        "env": {
            "USE_HEAVY": os.getenv("USE_HEAVY"),
            "ALLOW_FALLBACK": os.getenv("ALLOW_FALLBACK"),
            "AUDIOGEN_MODEL": os.getenv("AUDIOGEN_MODEL"),
        },
        "modules": {}
    }
    for m in ("torch","torchaudio","audiocraft"):
        try:
            importlib.import_module(m)
            info["modules"][m] = "ok"
        except Exception as e:
            info["modules"][m] = f"missing: {e}"
    return JSONResponse(info)

@router.get("/debug/routes", tags=["debug"])
def debug_routes(app=...):
    if app is ...:
        app = globals().get("app")
    routes = []
    try:
        for r in app.router.routes:  # type: ignore
            routes.append({"path": getattr(r, "path", ""), "methods": sorted(getattr(r, "methods", ["GET"]))})
    except Exception:
        pass
    return {"build": os.getenv("BUILD_TAG","dev"), "routes": routes}
