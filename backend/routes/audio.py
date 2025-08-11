# backend/routes/audio.py
import os, time
from urllib.parse import urljoin
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from backend.models.schemas import GenerateAudioRequest
from backend.services.generate import generate_file

router = APIRouter()
APP_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = APP_ROOT / "backend" / "output_audio"

@router.post("/generate-audio")
def generate_audio(payload: GenerateAudioRequest, request: Request):
    prompt = (payload.prompt or "").strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")
    if not (1 <= payload.duration <= 120):
        raise HTTPException(status_code=400, detail="Duration must be 1–120 seconds")

    t0 = time.time()
    out_path = generate_file(prompt, payload.duration, OUTPUT_DIR)

    base = os.getenv("PUBLIC_BASE_URL") or str(request.headers.get("X-Public-Base-Url") or "")
    rel = f"/audio/{out_path.stem}.wav"
    url = urljoin(base.rstrip('/') + '/', rel.lstrip('/')) if base else rel

    elapsed = int((time.time() - t0) * 1000)
    return JSONResponse(
        {"ok": True, "url": url, "path": str(out_path), "elapsed_ms": elapsed},
        headers={"X-Elapsed-Ms": str(elapsed)}
    )
