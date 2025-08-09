import os, logging, sys, platform
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from fastapi import FastAPI

from backend.routes.health import router as health_router
from backend.routes.audio import router as audio_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s :: %(message)s", stream=sys.stdout)

app = FastAPI(title="SoundForge.AI", version="0.1.0")

APP_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = APP_ROOT / "backend" / "output_audio"
FRONTEND_DIST = APP_ROOT / "frontend" / "dist"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Routers
app.include_router(health_router)                 # -> /health
app.include_router(health_router, prefix="/api")  # -> /api/health
app.include_router(audio_router,  prefix="/api")  # -> /api/generate-audio

# Serve audio and SPA (or landing)
app.mount("/audio", StaticFiles(directory=str(OUTPUT_DIR)), name="audio")
if FRONTEND_DIST.exists() and (FRONTEND_DIST / "index.html").exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")
else:
    @app.get("/", include_in_schema=False)
    def _landing():
        return HTMLResponse("<h1>SoundForge.AI backend is running</h1><p>No SPA build found. See <a href='/docs'>/docs</a>.</p>")

# Preload model if requested
@app.on_event("startup")
async def heavy_preflight():
    import os, importlib, logging
    if os.getenv("USE_HEAVY", "0") == "1":
        try:
            heavy = importlib.import_module("backend.services.heavy_audiogen")
            # will raise if CUDA/torch missing
            getattr(heavy, "_load_model")()
            logging.getLogger("uvicorn.error").info("✅ Heavy model loaded")
        except Exception as e:
            if os.getenv("ALLOW_FALLBACK", "0") != "1":
                raise
            logging.getLogger("uvicorn.error").warning(
                f"⚠️ Heavy preflight failed, ALLOW_FALLBACK=1: {e}"
            )

@app.get("/api/version", tags=["meta"])
def version():
    try:
        import torch
        cuda_available = torch.cuda.is_available()
        cuda_version = getattr(torch.version, "cuda", None)
        device_name = torch.cuda.get_device_name(0) if cuda_available else None
    except Exception:
        cuda_available, cuda_version, device_name = None, None, None
    try:
        from backend.services.heavy_audiogen import last_error
        try:
            last = last_error()
        except Exception as e:
            last = str(e)
    except Exception:
        last = None
    return JSONResponse(
        {
            "python": sys.version,
            "platform": platform.platform(),
            "use_heavy_env": os.getenv("USE_HEAVY", "0"),
            "allow_fallback": os.getenv("ALLOW_FALLBACK", ""),
            "audiogen_model": os.getenv("AUDIOGEN_MODEL", "facebook/audiogen-medium"),
            "cuda_available": cuda_available,
            "cuda_version": cuda_version,
            "device_name": device_name,
            "last_heavy_error": last,
        }
    )


@app.get("/api/debug/state", tags=["debug"])
def debug_state():
    import importlib

    def _chk(name: str) -> str:
        try:
            importlib.import_module(name)
            return "ok"
        except Exception as e:
            return f"missing: {e}"

    return JSONResponse(
        {
            "torch": _chk("torch"),
            "torchaudio": _chk("torchaudio"),
            "audiocraft": _chk("audiocraft"),
            "USE_HEAVY": os.getenv("USE_HEAVY", "0"),
            "ALLOW_FALLBACK": os.getenv("ALLOW_FALLBACK", ""),
            "AUDIOGEN_MODEL": os.getenv("AUDIOGEN_MODEL", "facebook/audiogen-medium"),
        }
    )

@app.post("/api/selftest", tags=["meta"])
def selftest():
    try:
        from backend.services.heavy_audiogen import generate_wav
        wav = generate_wav("leaves crunching under footsteps while walking, outdoors, dry leaves, close perspective",
                           seconds=2, sample_rate=22050, seed=42)
        return {"ok": True, "len": int(len(wav)), "sr": 22050}
    except Exception as e:
        return {"ok": False, "error": str(e)}
