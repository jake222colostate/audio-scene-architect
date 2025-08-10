import os, time, logging
from collections import deque
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from backend.utils.io import ensure_dir
from backend.routes import audio as audio_routes
from backend.routes import meta as meta_routes
from backend.routes import debug as debug_routes

LG = logging.getLogger("uvicorn.error")

def create_app() -> FastAPI:
    app = FastAPI(title="SoundForge.AI", version="1.0")

    app.state.start_time = time.time()
    app.state.recent_generations = deque(maxlen=10)
    app.state.heavy_logs = []
    app.state.last_heavy_error = None
    app.state.heavy_loaded = False
    app.state.audiogen_model = os.getenv("AUDIOGEN_MODEL", "facebook/audiogen-medium")
    app.state.audio_out_dir = Path(os.getenv("AUDIO_OUT_DIR", "backend/output_audio")).resolve()
    ensure_dir(app.state.audio_out_dir)

    # Static serving for generated audio
    app.mount("/audio", StaticFiles(directory=str(app.state.audio_out_dir)), name="audio")

    # Meta + debug on both / and /api; audio under /api only
    for prefix in ("", "/api"):
        app.include_router(meta_routes.router, prefix=prefix)
        app.include_router(debug_routes.router, prefix=prefix)
    app.include_router(audio_routes.router, prefix="/api")

    # Optional heavy preload
    if os.getenv("USE_HEAVY", "0") == "1":
        try:
            from backend.services import heavy_audiogen
            t0 = time.time()
            heavy_audiogen.load_model(app.state.audiogen_model)
            app.state.heavy_loaded = True
            app.state.last_heavy_error = None
            app.state.heavy_logs.append({
                "model": app.state.audiogen_model,
                "load_ms": int((time.time() - t0) * 1000),
            })
            LG.info("Heavy model loaded: %s", app.state.audiogen_model)
        except Exception as e:
            app.state.heavy_loaded = False
            app.state.last_heavy_error = str(e)
            LG.warning("Heavy preload failed: %s", e)

    return app
