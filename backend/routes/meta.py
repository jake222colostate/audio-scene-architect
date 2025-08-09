from fastapi import APIRouter
from fastapi.responses import JSONResponse
import os
from typing import Optional

router = APIRouter()

# updated by backend.main when heavy init fails
last_heavy_error: Optional[str] = None

@router.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}

@router.get("/version", tags=["meta"])
def version():
    build_tag = os.getenv("BUILD_TAG", "dev")
    use_heavy = os.getenv("USE_HEAVY", "0")
    allow_fallback = os.getenv("ALLOW_FALLBACK", "")
    cuda_available = False
    versions = {"torch": None, "torchaudio": None, "transformers": None, "tokenizers": None}
    try:
        import torch, torchaudio, transformers, tokenizers
        cuda_available = torch.cuda.is_available()
        versions = {
            "torch": torch.__version__,
            "torchaudio": torchaudio.__version__,
            "transformers": transformers.__version__,
            "tokenizers": tokenizers.__version__,
        }
    except Exception:
        pass
    payload = {
        "build_tag": build_tag,
        "cuda_available": cuda_available,
        "versions": versions,
        "use_heavy_env": use_heavy,
        "allow_fallback": allow_fallback,
        "last_heavy_error": last_heavy_error,
    }
    return JSONResponse(payload)
