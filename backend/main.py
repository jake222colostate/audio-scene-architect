import os, logging, uuid, time
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.exceptions import RequestValidationError
from starlette import status
from backend.routes.health import router as health_router
from backend.routes.audio import router as audio_router

APP_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = APP_ROOT / "backend" / "output_audio"
FRONTEND_DIST = APP_ROOT / "frontend" / "dist"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="SoundForge.AI", version="0.1.0")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    detail = []
    for e in exc.errors():
        loc = ".".join(str(p) for p in e.get("loc", []))
        msg = e.get("msg", "Invalid input")
        detail.append(f"{loc}: {msg}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"ok": False, "error": "Invalid request", "detail": detail},
    )

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


@app.get("/api/version", tags=["meta"])
def version():
    import os
    heavy_env = os.getenv("USE_HEAVY","0") == "1"
    try:
        import torch
        cuda_ok = torch.cuda.is_available()
        cuda_ver = getattr(torch.version, "cuda", None)
    except Exception:
        cuda_ok, cuda_ver = False, None
    try:
        from backend.services.heavy_audiogen import last_error
        last = last_error()
    except Exception:
        last = None
    return {"use_heavy_env": heavy_env, "cuda_available": cuda_ok, "cuda_version": cuda_ver, "last_heavy_error": last}


@app.get("/api/debug/generator", tags=["meta"])
def debug_generator():
    from backend.services import heavy_audiogen
    return {
        "device": "cuda" if __import__("torch").cuda.is_available() else "cpu",
        "model": os.getenv("AUDIOGEN_MODEL", "facebook/audiogen-medium"),
        "heavy_available": heavy_audiogen.is_available(),
        "last_heavy_error": heavy_audiogen.last_error(),
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
