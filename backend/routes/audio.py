import time
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from backend.models.schemas import GenerateAudioRequest
from backend.services.generate import generate_file
from pathlib import Path

router = APIRouter()

APP_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = APP_ROOT / "backend" / "output_audio"

@router.post("/generate-audio")
def generate_audio(payload: GenerateAudioRequest, request: Request):
    t0 = time.time()
    try:
        out_path = generate_file(payload.prompt, payload.duration, OUTPUT_DIR)
        url = f"/audio/{out_path.stem}.wav"
        elapsed = int((time.time() - t0) * 1000)
        return JSONResponse(
            {
                "ok": True,
                "url": url,
                "path": str(out_path),
                "elapsed_ms": elapsed,
            },
            headers={"X-Elapsed-Ms": str(elapsed)}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
