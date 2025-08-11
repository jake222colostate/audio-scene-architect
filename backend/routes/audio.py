# backend/routes/audio.py
import time
import uuid
from pathlib import Path
from typing import Literal
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from backend.models.schemas import GenerateAudioRequest
from backend.services.generate import generate_file as fallback_generate
from backend.services import heavy_audiogen as heavy
from backend.services.state import record_generation

router = APIRouter()
APP_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = APP_ROOT / "backend" / "output_audio"


def _policy(prefer: str | None) -> Literal["auto","heavy","fallback"]:
    p = (prefer or "auto").lower()
    return "heavy" if p == "heavy" else ("fallback" if p == "fallback" else "auto")


@router.post("/generate-audio")
def generate_audio(payload: GenerateAudioRequest, request: Request):
    prompt = (payload.prompt or "").strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")
    if not (1 <= payload.duration <= 120):
        raise HTTPException(status_code=400, detail="Duration must be 1–120 seconds")
    if payload.sample_rate is not None and not (8000 <= payload.sample_rate <= 48000):
        raise HTTPException(status_code=400, detail="sample_rate must be 8k–48k")

    prefer = request.query_params.get("prefer") or request.headers.get("X-Prefer-Heavy") or "auto"
    policy = _policy(prefer)

    t0 = time.time()
    generator = "fallback"

    # heavy path
    if policy in ("auto", "heavy"):
        try:
            if not heavy.is_ready():
                heavy.load_model()
            if heavy.is_ready():
                raw, sr = heavy.generate(prompt, payload.duration, payload.sample_rate)
                # Write to file
                OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
                file_id = str(uuid.uuid4())
                out_path = OUTPUT_DIR / f"{file_id}.wav"
                import numpy as np, soundfile as sf
                arr = np.frombuffer(raw, dtype=np.float32)
                sf.write(out_path, arr, sr, subtype="PCM_16")
                elapsed = int((time.time() - t0) * 1000)
                generator = "heavy"
                record_generation({
                    "prompt_hash": hash(prompt),
                    "duration": payload.duration,
                    "generator": generator,
                    "ms": elapsed,
                    "ok": True,
                })
                rel = f"/audio/{out_path.stem}.wav"
                return JSONResponse({
                    "ok": True,
                    "generator": generator,
                    "file_url": rel,
                    "duration": payload.duration,
                }, headers={"X-Elapsed-Ms": str(elapsed)})
            elif policy == "heavy":
                raise RuntimeError(heavy.last_heavy_error() or "heavy model unavailable")
        except Exception as e:
            if policy == "heavy":
                raise HTTPException(status_code=500, detail=f"heavy generation failed: {e}")
            # fall through to fallback

    # fallback path
    out_path = fallback_generate(prompt, payload.duration, OUTPUT_DIR, payload.sample_rate)
    elapsed = int((time.time() - t0) * 1000)
    record_generation({
        "prompt_hash": hash(prompt),
        "duration": payload.duration,
        "generator": generator,
        "ms": elapsed,
        "ok": True,
    })
    rel = f"/audio/{out_path.stem}.wav"
    return JSONResponse({
        "ok": True,
        "generator": generator,
        "file_url": rel,
        "duration": payload.duration,
    }, headers={"X-Elapsed-Ms": str(elapsed)})
