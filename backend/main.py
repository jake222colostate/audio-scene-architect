import os, sys, platform, importlib, logging
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from backend.routes.audio import router as audio_router

app = FastAPI(title="SoundForge.AI", version="0.1.0")

APP_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = APP_ROOT / "backend" / "output_audio"
FRONTEND_DIST = APP_ROOT / "frontend" / "dist"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s :: %(message)s", stream=sys.stdout)
BUILD_TAG = os.getenv("BUILD_TAG","dev")

# Include routers
app.include_router(audio_router, prefix="/api")

# Serve audio and SPA (or landing)
app.mount("/audio", StaticFiles(directory=str(OUTPUT_DIR)), name="audio")
if FRONTEND_DIST.exists() and (FRONTEND_DIST / "index.html").exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")
else:
    @app.get("/", include_in_schema=False)
    def _landing():
        return HTMLResponse("<h1>SoundForge.AI backend is running</h1><p>No SPA build found. See <a href='/docs'>/docs</a>.</p>")

@app.post("/api/debug/selftest", tags=["debug"])
def selftest():
    try:
        from backend.services.heavy_audiogen import generate_wav
        wav = generate_wav(
            "leaves crunching under footsteps while walking, outdoors, dry leaves, close perspective",
            seconds=2, sample_rate=22050, seed=42
        )
        return {"ok": True, "len": int(len(wav)), "sr": 22050, "generator": "heavy"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.get("/api/health", tags=["meta"])
def health():
    return {"ok": True, "build": BUILD_TAG}

def _detected_heavy_capable():
    try:
        import torch
        from audiocraft.models import AudioGen
        return bool(torch.cuda.is_available())
    except Exception:
        return False

@app.get("/api/version", tags=["meta"])
def version():
    cuda_ok = cuda_ver = dev = None
    tf_ver = tok_ver = None
    try:
        import torch; cuda_ok = torch.cuda.is_available()
        cuda_ver = getattr(torch.version, "cuda", None)
        dev = torch.cuda.get_device_name(0) if cuda_ok else None
    except Exception:
        pass
    try:
        import transformers, tokenizers
        tf_ver = transformers.__version__
        tok_ver = tokenizers.__version__
    except Exception:
        pass
    last = None
    try:
        heavy = importlib.import_module("backend.services.heavy_audiogen")
        last = getattr(heavy, "last_error")()
    except Exception:
        pass
    return {
        "python": sys.version, "platform": platform.platform(), "build": BUILD_TAG,
        "use_heavy_env": os.getenv("USE_HEAVY","0"), "allow_fallback": os.getenv("ALLOW_FALLBACK",""),
        "audiogen_model": os.getenv("AUDIOGEN_MODEL","facebook/audiogen-medium"),
        "cuda_available": cuda_ok, "cuda_version": cuda_ver, "device_name": dev,
        "transformers_version": tf_ver, "tokenizers_version": tok_ver,
        "detected_heavy_capable": _detected_heavy_capable(),
        "last_heavy_error": last
    }

@app.get("/api/debug/state", tags=["debug"])
def debug_state():
    info = {"env": {
        "USE_HEAVY": os.getenv("USE_HEAVY"),
        "ALLOW_FALLBACK": os.getenv("ALLOW_FALLBACK"),
        "AUDIOGEN_MODEL": os.getenv("AUDIOGEN_MODEL"),
    }, "modules": {}}
    for m in ("torch","torchaudio","audiocraft","transformers","tokenizers","sentencepiece"):
        try:
            importlib.import_module(m); info["modules"][m] = "ok"
        except Exception as e:
            info["modules"][m] = f"missing: {e}"
    return JSONResponse(info)

@app.on_event("startup")
async def _startup_diag():
    logging.getLogger("uvicorn.error").info(f"BUILD_TAG={BUILD_TAG}")
    try:
        import transformers, tokenizers
        logging.getLogger("uvicorn.error").info(
            f"HF stack: transformers={transformers.__version__} tokenizers={tokenizers.__version__}"
        )
    except Exception as e:
        logging.getLogger("uvicorn.error").warning(f"HF import failed: {e}")
    # Optional preload: do not crash on failure; we want server up for diagnostics
    if os.getenv("USE_HEAVY","0") == "1":
        try:
            heavy = importlib.import_module("backend.services.heavy_audiogen")
            getattr(heavy, "_load_model")()
            logging.getLogger("uvicorn.error").info("✅ Heavy model loaded")
        except Exception as e:
            logging.getLogger("uvicorn.error").warning(f"⚠️ Heavy preload failed: {e}")
