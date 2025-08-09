import os, sys, platform, importlib, logging
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from fastapi import FastAPI

from backend.routes.health import router as health_router
from backend.routes.audio import router as audio_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s :: %(message)s", stream=sys.stdout)
BUILD_TAG = os.getenv("BUILD_TAG", "dev")

app = FastAPI(title="SoundForge.AI", version="0.1.0")

APP_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = APP_ROOT / "backend" / "output_audio"
FRONTEND_DIST = APP_ROOT / "frontend" / "dist"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Routers
app.include_router(health_router)
app.include_router(health_router, prefix="/api")
app.include_router(audio_router, prefix="/api")

# Serve audio and SPA (or landing)
app.mount("/audio", StaticFiles(directory=str(OUTPUT_DIR)), name="audio")
if FRONTEND_DIST.exists() and (FRONTEND_DIST / "index.html").exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")
else:
    @app.get("/", include_in_schema=False)
    def _landing():
        return HTMLResponse("<h1>SoundForge.AI backend is running</h1><p>No SPA build found. See <a href='/docs'>/docs</a>.</p>")

@app.get("/api/version", tags=["meta"])
def version():
    cuda_ok = cuda_ver = dev = None
    try:
        import torch
        cuda_ok = torch.cuda.is_available()
        cuda_ver = getattr(torch.version, "cuda", None)
        dev = torch.cuda.get_device_name(0) if cuda_ok else None
    except Exception:
        pass
    last = None
    try:
        heavy = importlib.import_module("backend.services.heavy_audiogen")
        last = getattr(heavy, "last_error")()
    except Exception:
        pass
    return {
        "python": sys.version,
        "platform": platform.platform(),
        "build": BUILD_TAG,
        "use_heavy_env": os.getenv("USE_HEAVY", "0"),
        "allow_fallback": os.getenv("ALLOW_FALLBACK", ""),
        "audiogen_model": os.getenv("AUDIOGEN_MODEL", "facebook/audiogen-medium"),
        "cuda_available": cuda_ok,
        "cuda_version": cuda_ver,
        "device_name": dev,
        "last_heavy_error": last
    }

@app.get("/api/debug/state", tags=["debug"])
def debug_state():
    info = {
        "env": {
            "USE_HEAVY": os.getenv("USE_HEAVY"),
            "ALLOW_FALLBACK": os.getenv("ALLOW_FALLBACK"),
            "AUDIOGEN_MODEL": os.getenv("AUDIOGEN_MODEL"),
        },
        "modules": {}
    }
    for m in ("torch","torchaudio","audiocraft"):
        try:
            importlib.import_module(m)
            info["modules"][m] = "ok"
        except Exception as e:
            info["modules"][m] = f"missing: {e}"
    return JSONResponse(info)

@app.get("/api/debug/routes", tags=["debug"])
def debug_routes():
    routes = []
    for r in app.router.routes:
        routes.append({"path": getattr(r, "path", ""), "methods": sorted(getattr(r, "methods", ["GET"]))})
    return {"build": BUILD_TAG, "routes": routes}

@app.post("/api/debug/selftest", tags=["debug"])
def selftest():
    try:
        from backend.services.heavy_audiogen import generate_wav
        wav = generate_wav("leaves crunching under footsteps while walking, outdoors, dry leaves, close perspective", seconds=2, sample_rate=22050, seed=42)
        return {"ok": True, "len": int(len(wav)), "sr": 22050, "generator": "heavy"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.on_event("startup")
async def _startup_log_and_optional_preload():
    logging.getLogger("uvicorn.error").info(f"BUILD_TAG={BUILD_TAG}")
    for r in app.router.routes:
        methods = ",".join(sorted(getattr(r, "methods", ["GET"])))
        logging.getLogger("uvicorn.error").info("ROUTE %s %s", methods, getattr(r, "path", ""))
    if os.getenv("USE_HEAVY","0") == "1":
        try:
            heavy = importlib.import_module("backend.services.heavy_audiogen")
            getattr(heavy, "_load_model")()
            logging.getLogger("uvicorn.error").info("✅ Heavy model loaded")
        except Exception as e:
            if os.getenv("ALLOW_FALLBACK","0") != "1":
                logging.getLogger("uvicorn.error").error(f"❌ Heavy preflight failed (no fallback): {e}")
                raise
            logging.getLogger("uvicorn.error").warning(f"⚠️ Heavy preflight failed, ALLOW_FALLBACK=1: {e}")
