import os, logging, uuid, time
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, HTMLResponse
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

# Direct health endpoints (cannot disappear due to router mistakes)
@app.get("/api/health", tags=["health"])
def api_health():
    return {"status": "ok"}

@app.get("/health", tags=["health"])
def root_health():
    return {"status": "ok"}


@app.get("/api/version")
def version():
    import os
    try:
        import torch

        cuda_ok = torch.cuda.is_available()
        cuda = torch.version.cuda if cuda_ok else None
    except Exception:
        cuda_ok, cuda = False, None
    return {
        "use_heavy_env": os.getenv("USE_HEAVY", "0"),
        "cuda_available": cuda_ok,
        "cuda_version": cuda,
    }

# Routers (must be prefix-free inside files)
app.include_router(health_router)                 # -> /health
app.include_router(health_router, prefix="/api")  # -> /api/health
app.include_router(audio_router,  prefix="/api")  # -> /api/generate-audio

# Serve generated audio
app.mount("/audio", StaticFiles(directory=str(OUTPUT_DIR)), name="audio")

# Serve SPA at root if present; otherwise friendly landing page
if FRONTEND_DIST.exists() and (FRONTEND_DIST / "index.html").exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")
    logging.getLogger("uvicorn.error").info(f"🌐 Serving SPA from {FRONTEND_DIST}")
else:
    @app.get("/", include_in_schema=False)
    def landing():
        return HTMLResponse(
            "<!doctype html><meta charset='utf-8'>"
            "<title>SoundForge.AI</title>"
            "<h1>SoundForge.AI backend is running</h1>"
            "<p>No SPA build found at <code>/app/frontend/dist</code>. "
            "Visit <a href='/docs'>/docs</a> or POST to <code>/api/generate-audio</code>.</p>"
        )
    logging.getLogger("uvicorn.error").warning("⚠️ SPA not found; serving minimal landing page at '/'")

# Timing + request id headers
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
    logging.getLogger("uvicorn.error").info(
        "✅ Health at /api/health and /health; SPA served at / if /frontend/dist exists"
    )
