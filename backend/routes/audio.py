import os, time, importlib
from urllib.parse import urljoin
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from backend.models.schemas import GenerateAudioRequest
from backend.services.generate import generate_file

router = APIRouter()
APP_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = APP_ROOT / "backend" / "output_audio"

def _heavy_error_safe():
    try:
        heavy = importlib.import_module("backend.services.heavy_audiogen")
        return getattr(heavy, "last_error")()
    except Exception:
        return None

@router.post("/generate-audio")
def generate_audio(payload: GenerateAudioRequest, request: Request):
    try:
        t0 = time.time()
        out_path, generator = generate_file(
            payload.prompt, payload.duration, OUTPUT_DIR,
            sample_rate=payload.sample_rate, seed=payload.seed
        )
        base = os.getenv("PUBLIC_BASE_URL") or str(request.headers.get("X-Public-Base-Url") or "")
        rel = f"/audio/{out_path.stem}.wav"
        url = urljoin(base.rstrip('/') + '/', rel.lstrip('/')) if base else rel
        elapsed = int((time.time() - t0) * 1000)
        resp = {"ok": True, "url": url, "path": str(out_path), "elapsed_ms": elapsed, "generator": generator}
        he = _heavy_error_safe()
        if he is not None:
            resp["heavy_error"] = he
        return JSONResponse(resp, headers={"X-Elapsed-Ms": str(elapsed), "X-Generator": generator})
    except ValidationError as ve:
        raise HTTPException(status_code=422, detail=ve.errors())
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
