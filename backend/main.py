# backend/main.py
import logging, os, uuid, time
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from backend.routes.health import router as health_router
from backend.routes.audio import router as audio_router

APP_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = APP_ROOT / "backend" / "output_audio"
FRONTEND_DIST = APP_ROOT / "frontend" / "dist"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="SoundForge.AI", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

# Direct health endpoints (cannot disappear)
@app.get("/api/health", tags=["health"])
def api_health():
    return {"status": "ok"}

@app.get("/health", tags=["health"])
def root_health():
    return {"status": "ok"}

# Routers
app.include_router(health_router)                 # /health (dup OK)
app.include_router(health_router, prefix="/api")  # /api/health (dup OK)
app.include_router(audio_router,  prefix="/api")  # /api/generate-audio

# Static for generated audio
app.mount("/audio", StaticFiles(directory=str(OUTPUT_DIR)), name="audio")

# Serve built frontend (mount LAST so it never swallows /api/*)
if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")

# Timing + request id
@app.middleware("http")
async def timing(request: Request, call_next):
    rid = str(uuid.uuid4())[:8]
    start = time.time()
    try:
        resp = await call_next(request)
        resp.headers["X-Request-Id"] = rid
        resp.headers["X-Elapsed-Ms"] = str(int((time.time()-start)*1000))
        return resp
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e), "request_id": rid}, status_code=500)

# Route table logging on startup
@app.on_event("startup")
async def log_routes():
    lines = []
    for r in app.router.routes:
        methods = ",".join(sorted(getattr(r, "methods", ["GET"])))
        path = getattr(r, "path", "")
        lines.append(f"{methods:7s} {path}")
    logging.getLogger("uvicorn.error").info("Registered routes:\n" + "\n".join(lines))
    logging.getLogger("uvicorn.error").info("✅ Health at /api/health and /health")
