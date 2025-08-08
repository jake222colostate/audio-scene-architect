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

# Routers
app.include_router(health_router, prefix="/api")
app.include_router(audio_router, prefix="/api")

# Static mount for generated audio
app.mount("/audio", StaticFiles(directory=str(OUTPUT_DIR)), name="audio")

# Optionally serve frontend (if built)
if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")


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
