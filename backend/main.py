# backend/main.py
import logging
import os
import uuid
import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse

from backend.routes.health import router as health_router
from backend.routes.audio import router as audio_router

APP_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = APP_ROOT / "backend" / "output_audio"
FRONTEND_DIST = APP_ROOT / "frontend" / "dist"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="SoundForge.AI", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DISABLE_HEALTH = os.getenv("DISABLE_HEALTHCHECKS", "0") == "1"

# --- DIRECT health endpoints (cannot be hidden by bad router config) ---
if not DISABLE_HEALTH:
    @app.get("/api/health", tags=["health"])
    def api_health():
        return {"status": "ok"}

    @app.get("/health", tags=["health"])
    def root_health():
        return {"status": "ok"}

# --- Routers (backup; safe if someone edits them later) ---
if not DISABLE_HEALTH:
    app.include_router(health_router)                 # -> /health (again)
    app.include_router(health_router, prefix="/api")  # -> /api/health (again)
app.include_router(audio_router, prefix="/api")   # -> /api/generate-audio

# Static for generated audio
app.mount("/audio", StaticFiles(directory=str(OUTPUT_DIR)), name="audio")

# Frontend (mount LAST so it doesn't swallow /api/*)
if FRONTEND_DIST.exists():
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")
    index_file = FRONTEND_DIST / "index.html"
    if index_file.exists():
        @app.get("/")
        async def serve_root():
            return FileResponse(str(index_file))

        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str):
            if full_path.startswith("api"):
                return JSONResponse({"detail": "Not Found"}, status_code=404)
            return FileResponse(str(index_file))

# Request timing headers
@app.middleware("http")
async def timing(request: Request, call_next):
    req_id = str(uuid.uuid4())[:8]
    start = time.time()
    try:
        resp = await call_next(request)
        resp.headers["X-Request-Id"] = req_id
        resp.headers["X-Elapsed-Ms"] = str(int((time.time() - start) * 1000))
        return resp
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e), "request_id": req_id}, status_code=500)

# Route table logging on startup
@app.on_event("startup")
async def log_routes():
    lines = []
    for r in app.router.routes:
        methods = ",".join(sorted(getattr(r, "methods", ["GET"])))
        path = getattr(r, "path", "")
        lines.append(f"{methods:10s} {path}")
    logging.getLogger("uvicorn.error").info("Registered routes:\n" + "\n".join(lines))
    if not DISABLE_HEALTH:
        logging.getLogger("uvicorn.error").info("✅ Health at /api/health and /health")
    else:
        logging.getLogger("uvicorn.error").info("⚠️ Health checks disabled (DISABLE_HEALTHCHECKS=1)")
