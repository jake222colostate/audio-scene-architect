import os, sys, importlib, logging
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from backend.routes.audio import router as audio_router
from backend.routes import meta as meta_routes

app = FastAPI(title="SoundForge.AI", version="0.1.0")

APP_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = APP_ROOT / "backend" / "output_audio"
FRONTEND_DIST = APP_ROOT / "frontend" / "dist"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s :: %(message)s", stream=sys.stdout)
BUILD_TAG = os.getenv("BUILD_TAG","dev")

# Mount meta at both / and /api so /health and /api/health both work
app.include_router(meta_routes.router, prefix="")
app.include_router(meta_routes.router, prefix="/api")

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

@app.get("/api/debug/routes", tags=["debug"])
def debug_routes():
    items = []
    for r in app.router.routes:
        methods = sorted(getattr(r, "methods", ["GET"]))
        items.append({"path": getattr(r, "path", ""), "methods": methods})
    return JSONResponse(items)

@app.on_event("startup")
async def _log_routes_and_versions():
    import importlib
    lg = logging.getLogger("uvicorn.error")
    lg.info("BUILD_TAG=%s", BUILD_TAG)
    for r in app.router.routes:
        methods = ",".join(sorted(getattr(r, "methods", ["GET"])))
        lg.info("ROUTE %s %s", methods, getattr(r, "path", ""))
    try:
        import torch, torchaudio, transformers, tokenizers
        lg.info(
            "VERSIONS torch=%s torchaudio=%s transformers=%s tokenizers=%s",
            torch.__version__,
            torchaudio.__version__,
            transformers.__version__,
            tokenizers.__version__,
        )
    except Exception as e:
        lg.warning("Version logging failed: %s", e)
    if os.getenv("USE_HEAVY","0") == "1":
        try:
            heavy = importlib.import_module("backend.services.heavy_audiogen")
            getattr(heavy, "_load_model")()
            lg.info("✅ Heavy model loaded")
            meta_routes.last_heavy_error = None
        except Exception as e:
            meta_routes.last_heavy_error = str(e)
            lg.warning("⚠️ Heavy preload failed: %s", e)
