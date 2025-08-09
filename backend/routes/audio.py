import os, time
from urllib.parse import urljoin
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from backend.models.schemas import GenerateAudioRequest
from backend.services.generate import generate_file
from backend.services import heavy_audiogen

router = APIRouter()
APP_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = APP_ROOT / "backend" / "output_audio"

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
        headers = {"X-Elapsed-Ms": str(elapsed), "X-Generator": generator}
        return JSONResponse(
            {"ok": True, "url": url, "path": str(out_path), "elapsed_ms": elapsed,
             "generator": generator, "heavy_used": generator == "heavy", "heavy_error": heavy_audiogen.last_error()},
            headers=headers
        )
    except ValidationError as ve:
        raise HTTPException(status_code=422, detail=ve.errors())
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
