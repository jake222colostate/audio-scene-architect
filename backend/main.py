# backend/main.py
import os, logging, uuid, time, traceback
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.routing import APIRoute
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from backend.routes.health import router as health_router
from backend.routes.audio import router as audio_router
from backend.routes.meta import router as meta_router

# Runtime config and error state
USE_HEAVY = os.getenv("USE_HEAVY", "0")
ALLOW_FALLBACK = os.getenv("ALLOW_FALLBACK", "1")
BUILD_TAG = os.getenv("BUILD_TAG")
_last_error = {"msg": None, "trace": None}
_ready = False
STARTUP_COMPLETE = False
START_TIME = time.time()
MODE = "starting"  # one of: "heavy" | "fallback" | "starting"

def note_error(e: Exception):
    global _last_error
    _last_error = {
        "msg": f"{type(e).__name__}: {e}",
        "trace": "".join(traceback.format_exception(e))
    }

def get_last_error():
    return _last_error

def set_startup_complete(val: bool = True) -> None:
    global STARTUP_COMPLETE
    STARTUP_COMPLETE = bool(val)
APP_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = APP_ROOT / "backend" / "output_audio"
# Support both container path (/frontend/dist) and local build path (/dist)
FRONTEND_CANDIDATES = [
    APP_ROOT / "frontend" / "dist",
    APP_ROOT / "dist",
]

def _find_frontend_dist():
    for p in FRONTEND_CANDIDATES:
        if p.exists():
            return p
    return None

def create_app() -> FastAPI:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    app = FastAPI(title="SoundForge.AI", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"], allow_credentials=True,
        allow_methods=["*"], allow_headers=["*"],
    )

    # Direct health endpoints (liveness) and readiness
    @app.get("/api/health", tags=["health"])  # type: ignore[misc]
    def api_health():
        return {"status": "ok", "uptime_sec": round(time.time() - START_TIME, 1), "mode": MODE}

    @app.get("/api/ready", tags=["health"])  # type: ignore[misc]
    def api_ready():
        if not _ready:
            raise HTTPException(status_code=503, detail={"ready": False, "mode": MODE, "last_error": _last_error})
        return {"ready": True, "mode": MODE, "last_error": _last_error}

    @app.get("/health", tags=["health"])  # type: ignore[misc]
    def root_health():
        if not STARTUP_COMPLETE:
            return JSONResponse({"status": "starting"}, status_code=503)
        return {"status": "ok"}

    # Routers
    app.include_router(health_router)                 # -> /health
    app.include_router(health_router, prefix="/api")  # -> /api/health
    app.include_router(audio_router,  prefix="/api")  # -> /api/generate-audio
    app.include_router(meta_router)                   # /version + /api/* debug

    # Static for generated audio
    app.mount("/audio", StaticFiles(directory=str(OUTPUT_DIR)), name="audio")

    # Serve SPA at root — mount LAST so it never swallows /api/*
    dist = _find_frontend_dist()
    if dist:
        app.mount("/", StaticFiles(directory=str(dist), html=True), name="frontend")
    # Add timing + request id
    @app.middleware("http")
    async def timing(request: Request, call_next):  # type: ignore[misc]
        rid = str(uuid.uuid4())[:8]
        start = time.time()
        try:
            resp = await call_next(request)
            resp.headers["X-Request-Id"] = rid
            resp.headers["X-Elapsed-Ms"] = str(int((time.time()-start)*1000))
            return resp
        except Exception as e:  # noqa: BLE001
            return JSONResponse({"ok": False, "error": str(e), "request_id": rid}, status_code=500)

    # Route table logging on startup
    @app.on_event("startup")
    async def log_routes():  # type: ignore[misc]
        lines = []
        for r in app.router.routes:
            methods = ",".join(sorted(getattr(r, "methods", ["GET"])))
            path = getattr(r, "path", "")
            lines.append(f"{methods:7s} {path}")
        logging.getLogger("uvicorn.error").info("Registered routes:\n" + "\n".join(lines))
        logging.getLogger("uvicorn.error").info("✅ Health at /api/health and /health; SPA served if a dist folder is present")

    # Readiness + heavy init
    @app.on_event("startup")
    async def startup():  # type: ignore[misc]
        global _ready, MODE
        try:
            routes = [f"{','.join(sorted(r.methods))} {r.path}" for r in app.routes if isinstance(r, APIRoute)]
            print("[STARTUP] Routes:\n" + "\n".join(sorted(routes)))
            use_heavy = os.getenv("USE_HEAVY", "0") == "1"
            allow_fallback = os.getenv("ALLOW_FALLBACK", "1") == "1"
            if use_heavy:
                try:
                    import importlib
                    import torch
                    _ = torch.cuda.is_available()
                    importlib.import_module("audiocraft")
                    MODE = "heavy"
                    _ready = True
                except Exception as e:
                    note_error(e)
                    if allow_fallback:
                        MODE = "fallback"
                        _ready = True
                    else:
                        MODE = "starting"
                        _ready = False
            else:
                MODE = "fallback"
                _ready = True
        finally:
            set_startup_complete(True)
    return app


# Uvicorn entrypoint
app = create_app()
