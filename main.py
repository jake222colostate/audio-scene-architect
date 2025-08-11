"""Streamlined main FastAPI application file."""
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

# Import configuration and setup
from config import BASE_DIR, OUTPUT_DIR
from services.job_processor import start_job_processor
from routes.health import router as health_router
from routes.audio import router as audio_router

# Verify FFmpeg availability at startup
try:
    import ffmpeg
    print("[STARTUP] FFmpeg Python wrapper available")
except Exception:
    from shutil import which
    if not which("ffmpeg"):
        print("[STARTUP] ❌ FFMPEG not installed or not in PATH")
        raise RuntimeError("❌ FFMPEG not installed or not in PATH.")
    else:
        print("[STARTUP] FFmpeg binary found in PATH")

# Create FastAPI app
app = FastAPI()

# Health check route
@app.get("/health")
def health_check():
    return {"status": "ok"}

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend assets
frontend_dir = os.path.join(os.path.dirname(__file__), "dist")
if os.path.exists(frontend_dir):
    print(f"[STARTUP] Frontend build found at {frontend_dir}; mounting /assets")
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dir, "assets")), name="assets")
else:
    print(f"[STARTUP] ⚠️ Frontend build not found at {frontend_dir}")

# Serve generated audio files
if OUTPUT_DIR.exists():
    print(f"[STARTUP] Mounting generated audio from {OUTPUT_DIR} at /audio")
    app.mount("/audio", StaticFiles(directory=str(OUTPUT_DIR)), name="audio")
else:
    print(f"[STARTUP] ⚠️ OUTPUT_DIR not found at {OUTPUT_DIR}")

# Include routers
app.include_router(health_router)
app.include_router(audio_router)

# Create API router for additional endpoints
router = APIRouter(prefix="/api")
app.include_router(router)

@app.on_event("startup")
def startup_event():
    """Initialize background services on startup."""
    start_job_processor()

# Serve frontend for all unmatched routes (SPA support)
@app.get("/{path:path}")
async def serve_frontend(path: str):
    """Serve the frontend for SPA routing."""
    frontend_file = os.path.join(frontend_dir, "index.html")
    if os.path.exists(frontend_file):
        print(f"[FRONTEND] Serving React app for path: /{path}")
        from fastapi.responses import FileResponse
        return FileResponse(frontend_file)
    print("[FRONTEND] Frontend not found; dist directory missing")
    return {"message": "Frontend not found"}