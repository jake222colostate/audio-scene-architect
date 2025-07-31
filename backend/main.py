from fastapi import FastAPI, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pathlib import Path
import random
import shutil
from datetime import datetime
import uuid
import os
import logging
import traceback
import datetime as _dt
from pydub import AudioSegment

REQUIRED_DIRS = ["output_audio", "sample_audio", "audioldm/weights"]

for directory in REQUIRED_DIRS:
    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)

try:
    from audiocraft.models import musicgen
except Exception as e:
    raise RuntimeError("\u274c AudioCraft is not installed or importable.")

try:
    from audioldm import AudioLDM
except Exception as e:
    raise RuntimeError("\u274c AudioLDM is not installed or importable.")

try:
    import ffmpeg
except Exception:
    from shutil import which
    if not which("ffmpeg"):
        raise RuntimeError("\u274c FFMPEG not installed or not in PATH.")


app = FastAPI()

logging.basicConfig(level=logging.INFO)

# Allow all origins/headers during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).parent
SAMPLE_DIR = BASE_DIR / "sample_audio"
OUTPUT_DIR = BASE_DIR / "output_audio"
LOG_FILE = BASE_DIR / "audio_logs.txt"
ERROR_LOG = BASE_DIR / "error_log.txt"


def log_error(msg: str) -> None:
    with ERROR_LOG.open("a") as f:
        f.write(f"[{_dt.datetime.now()}] {msg}\n")

# Predefined horror prompts for SFX generation
sfx_prompts = [
    "distant whisper",
    "footsteps on old wood",
    "metal door slam",
    "wind howling through trees",
    "low breathing",
    "creaking floorboards",
]

# Ensure directories exist
SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def generate_sfx_clip(prompt: str, duration: int) -> str:
    try:
        import uuid as _uuid
        import os
        import torchaudio

        model = AudioLDM()
        audio = model.generate(prompt=prompt, duration=duration)

        filename = f"{_uuid.uuid4()}_sfx.wav"
        filepath = os.path.join("output_audio", filename)

        torchaudio.save(filepath, audio.squeeze(0), 16000)
        return filepath
    except Exception as e:
        log_error(f"SFX Failed | Prompt: {prompt}\n{traceback.format_exc()}")
        return None


def generate_audio_from_text(prompt: str, duration: int):
    """Generate an audio file from text using AudioCraft."""
    try:
        from audiocraft.data.audio import audio_write

        model = musicgen.MusicGen.get_pretrained("small")
        model.set_generation_params(duration=duration)

        wav = model.generate_with_chroma([prompt])

        filename = f"{uuid.uuid4()}.wav"
        filepath = OUTPUT_DIR / filename

        audio_write(str(filepath.with_suffix("")), wav[0].cpu(), model.sample_rate, strategy="loudness")

        mp3_filename = filepath.with_suffix(".mp3").name
        mp3_path = OUTPUT_DIR / mp3_filename
        AudioSegment.from_wav(filepath).export(mp3_path, format="mp3")
        os.remove(filepath)

        base_audio = AudioSegment.from_mp3(mp3_path)

        sfx_used = []
        for _ in range(random.randint(1, 2)):
            s_prompt = random.choice(sfx_prompts)
            sfx_used.append(s_prompt)
            try:
                sfx_file = generate_sfx_clip(s_prompt, 3)
                if sfx_file:
                    overlay = AudioSegment.from_wav(sfx_file) - 8
                    start_ms = random.randint(0, max(0, len(base_audio) - len(overlay)))
                    base_audio = base_audio.overlay(overlay, position=start_ms)
                    os.remove(sfx_file)
            except Exception:
                continue

        final_name = f"{uuid.uuid4()}.mp3"
        final_path = OUTPUT_DIR / final_name
        base_audio.export(final_path, format="mp3")
        os.remove(mp3_path)

        return final_name, sfx_used
    except Exception:
        log_error(f"AudioCraft Failed | Prompt: {prompt}\n{traceback.format_exc()}")
        fallback = SAMPLE_DIR / "fallback.mp3"
        if fallback.exists():
            dest = OUTPUT_DIR / f"{uuid.uuid4()}.mp3"
            shutil.copy(fallback, dest)
            return dest.name, []
        raise HTTPException(status_code=500, detail="AudioCraft generation failed.")

@app.post("/generate-audio")
async def generate_audio(prompt: str = Form(...), duration: int = Form(...)):
    if duration not in {30, 60, 90, 120}:
        raise HTTPException(status_code=400, detail="Invalid duration. Must be 30, 60, 90, or 120 seconds")

    try:
        filename, sfx_layers = generate_audio_from_text(prompt, duration)
        status = "success"
    except Exception as exc:
        log_error(f"POST /generate-audio failed: {exc}")
        raise HTTPException(status_code=500, detail="Internal generation error")
    output_file = OUTPUT_DIR / filename

    # Append log
    with LOG_FILE.open("a") as logf:
        timestamp = datetime.utcnow().isoformat()
        sfx_str = ",".join(sfx_layers) if sfx_layers else "none"
        logf.write(
            f"[{timestamp}] {prompt} | {filename} | {sfx_str} | {status}\n"
        )

    return JSONResponse({
        "file_url": f"/download/{filename}",
        "sfx": sfx_layers,
        "status": status,
    })

@app.get("/download/{filename}")
async def download(filename: str):
    file_path = OUTPUT_DIR / filename
    if not file_path.exists() or file_path.suffix != ".mp3":
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, media_type="audio/mpeg", filename=filename)


@app.get("/diagnostic")
def run_tests():
    results = []

    try:
        model = musicgen.MusicGen.get_pretrained('small')
        model.set_generation_params(duration=5)
        model.generate(["test audio"])
        results.append("\u2705 AudioCraft OK")
    except Exception:
        results.append("\u274c AudioCraft FAILED")

    try:
        model = AudioLDM()
        model.generate("test sfx", duration=2)
        results.append("\u2705 AudioLDM OK")
    except Exception:
        results.append("\u274c AudioLDM FAILED")

    for d in REQUIRED_DIRS:
        results.append(f"\u2705 Found {d}" if os.path.exists(d) else f"\u274c Missing {d}")

    return {"results": results}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

