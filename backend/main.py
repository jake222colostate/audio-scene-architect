import os
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from starlette.responses import JSONResponse
from starlette.middleware import Middleware
import logging

from backend.routes.health import router as health_router
from backend.routes.audio import router as audio_router

APP_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = APP_ROOT / "backend" / "output_audio"
FRONTEND_DIST = APP_ROOT / "frontend" / "dist"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
]

app = FastAPI(title="SoundForge.AI", version="0.1.0", middleware=middleware)
logging.getLogger("uvicorn.error").info("✅ FastAPI started — health at /api/health (and /health)")

# Routers
app.include_router(health_router)                 # /health
app.include_router(health_router, prefix="/api")  # /api/health
app.include_router(audio_router, prefix="/api")

# Static mount for generated audio
app.mount("/audio", StaticFiles(directory=str(OUTPUT_DIR)), name="audio")

# Optionally serve frontend (if built)
if FRONTEND_DIST.exists():
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.exists():
        print(f"[STARTUP] Serving frontend assets from {assets_dir} at /assets")
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")
    index_file = FRONTEND_DIST / "index.html"
    if index_file.exists():
        print(f"[STARTUP] Frontend index found at {index_file}; enabling SPA fallback")

        @app.get("/")
        async def serve_root():
            print("[FRONTEND] Serving index.html for /")
            return FileResponse(str(index_file))

        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str):
            # Let API routes be handled by routers, not the SPA fallback
            if full_path.startswith("api"):
                return JSONResponse({"detail": "Not Found"}, status_code=404)
            print(f"[FRONTEND] SPA fallback for /{full_path}")
            return FileResponse(str(index_file))
    else:
        print(f"[STARTUP] ⚠️ Frontend index not found at {index_file}")
else:
    print(f"[STARTUP] ⚠️ FRONTEND_DIST not found at {FRONTEND_DIST}")

    @app.get("/")
    async def root_ok():
        # If no frontend is built, still serve 200 OK at root for probes
        return JSONResponse({"status": "ok"})


@app.middleware("http")
async def add_request_id_logging(request: Request, call_next):
    req_id = str(uuid.uuid4())[:8]
    start = time.time()
    response = None
    try:
        response = await call_next(request)
        elapsed = int((time.time() - start) * 1000)
        response.headers["X-Request-Id"] = req_id
        response.headers["X-Elapsed-Ms"] = str(elapsed)
        return response
    except Exception as e:
        elapsed = int((time.time() - start) * 1000)
        return JSONResponse(
            {"ok": False, "error": str(e), "request_id": req_id, "elapsed_ms": elapsed},
            status_code=500,
        )
