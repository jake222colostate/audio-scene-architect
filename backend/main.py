# backend/main.py
import logging
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

# --- Register routes (order matters) ---
# Health: both /health and /api/health
app.include_router(health_router)                 # -> /health
app.include_router(health_router, prefix="/api")  # -> /api/health

# API routes
app.include_router(audio_router, prefix="/api")   # -> /api/generate-audio

# Static for generated audio
app.mount("/audio", StaticFiles(directory=str(OUTPUT_DIR)), name="audio")

# Frontend (optional) — mount last so it doesn't swallow /api/*
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

# Request timing + request-id headers
@app.middleware("http")
async def add_request_id_logging(request: Request, call_next):
    req_id = str(uuid.uuid4())[:8]
    start = time.time()
    try:
        response = await call_next(request)
        response.headers["X-Request-Id"] = req_id
        response.headers["X-Elapsed-Ms"] = str(int((time.time() - start) * 1000))
        return response
    except Exception as e:
        return JSONResponse(
            {"ok": False, "error": str(e), "request_id": req_id},
            status_code=500,
        )

# Log the route table at startup
@app.on_event("startup")
async def log_routes():
    routes = []
    for r in app.router.routes:
        methods = ",".join(sorted(getattr(r, "methods", ["GET"])))
        path = getattr(r, "path", "")
        routes.append(f"{methods:10s} {path}")
    logging.getLogger("uvicorn.error").info("Registered routes:\n" + "\n".join(routes))
    logging.getLogger("uvicorn.error").info("✅ Health at /api/health and /health")
