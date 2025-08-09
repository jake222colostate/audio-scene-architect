from fastapi import APIRouter
from fastapi.responses import JSONResponse
import os, sys, platform, importlib

router = APIRouter()

def _torch_info():
    ok = ver = dev = cuda = None
    try:
        import torch
        ok = True
        cuda = torch.cuda.is_available()
        ver = getattr(torch.version, "cuda", None)
        dev = torch.cuda.get_device_name(0) if cuda else None
    except Exception:
        pass
    return {"cuda_available": cuda, "cuda_version": ver, "device_name": dev}

def _heavy_last():
    try:
        heavy = importlib.import_module("backend.services.heavy_audiogen")
        return getattr(heavy, "last_error")()
    except Exception:
        return None

def _hf_versions():
    tf = tok = None
    try:
        import transformers, tokenizers
        tf, tok = transformers.__version__, tokenizers.__version__
    except Exception:
        pass
    return {"transformers_version": tf, "tokenizers_version": tok}

@router.get("/health", tags=["meta"])
def health():
    return {"ok": True, "build": os.getenv("BUILD_TAG", "dev")}

@router.get("/version", tags=["meta"])
def version():
    return JSONResponse({
        "python": sys.version,
        "platform": platform.platform(),
        "build": os.getenv("BUILD_TAG","dev"),
        "use_heavy_env": os.getenv("USE_HEAVY","0"),
        "allow_fallback": os.getenv("ALLOW_FALLBACK",""),
        "audiogen_model": os.getenv("AUDIOGEN_MODEL","facebook/audiogen-medium"),
        **_torch_info(),
        **_hf_versions(),
        "last_heavy_error": _heavy_last()
    })
