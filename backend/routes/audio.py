import os
import time
from urllib.parse import urljoin
import soundfile as sf
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from backend.models.schemas import GenerateAudioRequest
from backend.services import heavy_audiogen, fallback_procedural
from backend.utils.io import uuid_filename

router = APIRouter()

def _record(app, prompt, duration, generator, ms, ok):
    app.state.recent_generations.append({
        "prompt_hash": hash(prompt) & 0xFFFFFFFF,
        "duration": int(duration),
        "generator": generator,
        "ms": int(ms),
        "ok": bool(ok),
    })

@router.post("/generate-audio", tags=["audio"])
def generate_audio(request: Request, payload: GenerateAudioRequest):
    app = request.app
    t0 = time.time()
    try:
        base = (getattr(app.state, "public_base_url", None)
                or getattr(app.state, "PUBLIC_BASE_URL", None)
                or None)
        sr = int(payload.sample_rate or 44100)
        generator = "fallback"
        y = None

        use_heavy = (str(getattr(app.state, "heavy_loaded", False)).lower() == "true") or \
                    (heavy_audiogen.is_ready())

        if (use_heavy or (use_heavy is False and (str.__eq__(os.getenv("USE_HEAVY","0"), "1")))):
            try:
                y = heavy_audiogen.generate(payload.prompt, payload.duration, sr=sr)
                generator = "heavy"
            except Exception as e:
                app.state.last_heavy_error = str(e)
                if os.getenv("ALLOW_FALLBACK", "1") != "1":
                    raise

        if y is None:
            # procedural fallback path
            out_path = fallback_procedural.generate(payload.prompt, payload.duration, app.state.audio_out_dir, sr=sr)
        else:
            # write numpy -> wav
            out_path = app.state.audio_out_dir / uuid_filename(".wav")
            sf.write(out_path, y, sr)

        elapsed = int((time.time() - t0) * 1000)
        rel = f"/audio/{out_path.name}"
        file_url = urljoin(base.rstrip('/') + '/', rel.lstrip('/')) if base else rel

        _record(app, payload.prompt, payload.duration, generator, elapsed, True)
        resp = {"ok": True, "generator": generator, "file_url": file_url, "duration": payload.duration}
        if app.state.last_heavy_error:
            resp["last_heavy_error"] = app.state.last_heavy_error
        return JSONResponse(resp, headers={"X-Elapsed-Ms": str(elapsed), "X-Generator": generator})
    except ValidationError as ve:
        raise HTTPException(status_code=422, detail=ve.errors())
    except HTTPException:
        raise
    except Exception as e:
        _record(app, payload.prompt, payload.duration, "error", int((time.time() - t0) * 1000), False)
        raise HTTPException(status_code=500, detail=str(e))
