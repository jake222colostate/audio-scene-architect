import time
import hashlib
from urllib.parse import urljoin
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError
import soundfile as sf

from backend.models.schemas import GenerateAudioRequest
from backend.services import heavy_audiogen, fallback_procedural
from backend.utils.io import uuid_filename


router = APIRouter()


def _record(app, prompt: str, duration: int, generator: str, ms: int, ok: bool):
    app.state.recent_generations.append({
        "prompt": hashlib.sha256(prompt.encode()).hexdigest()[:8],
        "duration": duration,
        "generator": generator,
        "ms": ms,
        "ok": ok,
    })


@router.post("/generate-audio")
def generate_audio(payload: GenerateAudioRequest, request: Request):
    t0 = time.time()
    app = request.app
    out_dir = app.state.audio_out_dir
    base = app.state.public_base_url or str(request.headers.get("X-Public-Base-Url") or "")
    try:
        if app.state.use_heavy == "1":
            try:
                wav = heavy_audiogen.generate(payload.prompt, payload.duration, sr=payload.sample_rate)
                out_path = out_dir / uuid_filename(".wav")
                sf.write(out_path, wav, payload.sample_rate, subtype="PCM_16")
                generator = "heavy"
                app.state.last_heavy_error = None
            except heavy_audiogen.HeavyLoadError as e:
                app.state.last_heavy_error = str(e)
                if app.state.allow_fallback == "1":
                    out_path = fallback_procedural.generate(payload.prompt, payload.duration, out_dir, sr=payload.sample_rate)
                    generator = "fallback"
                else:
                    _record(app, payload.prompt, payload.duration, "heavy", int((time.time()-t0)*1000), False)
                    return JSONResponse({"ok": False, "error": "HEAVY_FAILED", "message": str(e)}, status_code=500)
        else:
            out_path = fallback_procedural.generate(payload.prompt, payload.duration, out_dir, sr=payload.sample_rate)
            generator = "fallback"

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
        _record(app, payload.prompt, payload.duration, "error", int((time.time()-t0)*1000), False)
        raise HTTPException(status_code=500, detail=str(e))
