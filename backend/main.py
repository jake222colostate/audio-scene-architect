import os
import pathlib
from datetime import datetime

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.routes.audio import router as audio_router
from backend.routes.meta import router as meta_router


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]


def resolve_front_dir() -> str:
    env_dir = os.getenv("FRONT_DIR")
    candidates = [
        env_dir,
        str(REPO_ROOT / "frontend" / "dist"),
        str(REPO_ROOT / "dist"),
    ]
    for p in candidates:
        if p and os.path.exists(os.path.join(p, "index.html")):
            return p
    return str(REPO_ROOT / "frontend" / "dist")


FRONT_DIR = resolve_front_dir()
OUTPUT_DIR = str(REPO_ROOT / "backend" / "output_audio")
os.makedirs(OUTPUT_DIR, exist_ok=True)

AUDIO_PROVIDER = os.getenv("AUDIO_PROVIDER", "procedural")


def _lazy_video_tools():
    def _noop(_: str):
        return []

    get_speech_segments = None
    get_vad_only_segments = _noop
    detect_scene_changes = _noop
    detect_motion_cues = _noop

    try:
        from .design.vad_asr import (
            get_speech_segments as _gss,
            get_vad_only_segments as _gv,
        )

        get_speech_segments, get_vad_only_segments = _gss, _gv
    except Exception as e:  # pragma: no cover - optional dependency
        print(f"[VIDEO] Whisper/VAD unavailable: {e} — using VAD-only/noop")

    try:
        from .design.scene_detect import (
            detect_scene_changes as _sc,
            detect_motion_cues as _mc,
        )

        detect_scene_changes, detect_motion_cues = _sc, _mc
    except Exception as e:  # pragma: no cover - optional dependency
        print(f"[VIDEO] OpenCV cues unavailable: {e} — skipping cues")

    return (
        get_speech_segments,
        get_vad_only_segments,
        detect_scene_changes,
        detect_motion_cues,
    )


app = FastAPI()

app.mount("/audio", StaticFiles(directory=OUTPUT_DIR), name="audio")
app.mount("/", StaticFiles(directory=FRONT_DIR, html=True), name="frontend")


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "time": datetime.utcnow().isoformat() + "Z",
        "front_dir": FRONT_DIR,
    }


class VideoRequest(BaseModel):
    audio_path: str
    video_path: str


@app.post("/api/design/video")
def design_video(req: VideoRequest):
    gss, gv_only, scene_fn, motion_fn = _lazy_video_tools()
    use_vad_only = (
        os.getenv("USE_VAD_ONLY", "false").lower() == "true"
    ) or (gss is None)
    speech_segments = gv_only(req.audio_path) if use_vad_only else gss(req.audio_path)
    scene_segments = scene_fn(req.video_path)
    motion_cues = motion_fn(req.video_path)
    return {
        "speech_segments": speech_segments,
        "scene_segments": scene_segments,
        "motion_cues": motion_cues,
    }


app.include_router(audio_router, prefix="/api")
app.include_router(meta_router)

