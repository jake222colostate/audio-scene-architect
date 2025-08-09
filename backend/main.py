import os, sys, importlib, logging
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from fastapi import FastAPI

from backend.routes import meta as meta_routes
from backend.routes.audio import router as audio_router

app = FastAPI(title="SoundForge.AI", version="0.1.0")

APP_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = APP_ROOT / "backend" / "output_audio"
FRONTEND_DIST = APP_ROOT / "frontend" / "dist"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Build tag for verification
BUILD_TAG = os.getenv("BUILD_TAG", "dev")

# Include routers
app.include_router(meta_routes.router, prefix="/api")
setattr(meta_routes, "app", app)
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

# Log routes at startup and optionally preload heavy
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s :: %(message)s", stream=sys.stdout)

@app.on_event("startup")
async def _preflight():
    logging.getLogger("uvicorn.error").info(f"BUILD_TAG={BUILD_TAG}")
    for r in app.router.routes:
        methods = ",".join(sorted(getattr(r, "methods", ["GET"])))
        logging.getLogger("uvicorn.error").info("ROUTE %s %s", methods, getattr(r, "path", ""))
    try:
        import transformers
        logging.getLogger("uvicorn.error").info(f"Transformers version: {transformers.__version__}")
    except Exception as e:
        logging.getLogger("uvicorn.error").warning(f"Transformers import failed: {e}")
    if os.getenv("USE_HEAVY","0") == "1":
        try:
            heavy = importlib.import_module("backend.services.heavy_audiogen")
            getattr(heavy, "_load_model")()
            logging.getLogger("uvicorn.error").info("✅ Heavy model loaded")
        except Exception as e:
            logging.getLogger("uvicorn.error").warning(f"⚠️ Heavy preload failed: {e}")
            # do NOT raise; server must stay up
