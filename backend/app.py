import os
import sys
import time
import logging
from collections import deque
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from backend.utils.io import ensure_dir
from backend.routes import audio, meta, debug


def create_app() -> FastAPI:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
        stream=sys.stdout,
    )

    app = FastAPI(title="SoundForge.AI", version="0.1.0")

    app.state.start_time = time.time()
    app.state.recent_generations = deque(maxlen=10)
    app.state.last_heavy_error = None
    app.state.heavy_loaded = False
    app.state.heavy_logs = []

    app.state.use_heavy = os.getenv("USE_HEAVY", "0")
    app.state.allow_fallback = os.getenv("ALLOW_FALLBACK", "0")
    app.state.audiogen_model = os.getenv("AUDIOGEN_MODEL", "facebook/audiogen-medium")
    app.state.public_base_url = os.getenv("PUBLIC_BASE_URL")

    audio_out = os.getenv("AUDIO_OUT_DIR") or str(Path(__file__).parent / "output_audio")
    app.state.audio_out_dir = ensure_dir(Path(audio_out))

    # Mount routers
    app.include_router(meta.router, prefix="")
    app.include_router(meta.router, prefix="/api")
    app.include_router(debug.router, prefix="/api")
    app.include_router(audio.router, prefix="/api")

    # Static mounts
    app.mount("/audio", StaticFiles(directory=str(app.state.audio_out_dir)), name="audio")

    frontend_dist = Path(__file__).resolve().parents[1] / "frontend" / "dist"
    if frontend_dist.exists() and (frontend_dist / "index.html").exists():
        app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
    else:
        @app.get("/", include_in_schema=False)
        def _landing():
            return HTMLResponse(
                "<h1>SoundForge.AI backend is running</h1><p>No SPA build found. See <a href='/docs'>/docs</a>.</p>"
            )

    @app.on_event("startup")
    async def _startup_logs() -> None:
        from backend.utils.diagnostics import gather_version_payload
        lg = logging.getLogger("uvicorn.error")
        lg.info("Routes:")
        for r in app.router.routes:
            methods = ",".join(sorted(getattr(r, "methods", ["GET"])))
            lg.info(" %s %s", methods, getattr(r, "path", ""))
        lg.info("Env USE_HEAVY=%s ALLOW_FALLBACK=%s AUDIOGEN_MODEL=%s PUBLIC_BASE_URL=%s AUDIO_OUT_DIR=%s",
                app.state.use_heavy, app.state.allow_fallback, app.state.audiogen_model,
                app.state.public_base_url, app.state.audio_out_dir)
        info = gather_version_payload(app)
        lg.info("Versions python=%s torch=%s torchaudio=%s transformers=%s tokenizers=%s audiocraft=%s",
                info.get("python_version"), info.get("torch_version"), info.get("torchaudio_version"),
                info.get("transformers_version"), info.get("tokenizers_version"), info.get("audiocraft_version"))
        if app.state.use_heavy == "1":
            try:
                from backend.services import heavy_audiogen
                t0 = time.time()
                heavy_audiogen.load_model(app.state.audiogen_model)
                app.state.heavy_loaded = True
                app.state.last_heavy_error = None
                app.state.heavy_logs.append({"model": app.state.audiogen_model, "load_ms": int((time.time()-t0)*1000)})
                lg.info("Heavy model loaded")
            except Exception as e:
                app.state.heavy_loaded = False
                app.state.last_heavy_error = str(e)
                lg.warning("Heavy preload failed: %s", e)

    return app
