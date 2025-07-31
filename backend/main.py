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
import datetime, traceback
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


def log_error(tag: str, err: Exception) -> None:
    with open("error_log.txt", "a") as f:
        f.write(f"[{datetime.datetime.now()}] {tag}\n")
        f.write(traceback.format_exc() + "\n")

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
        log_error(f"SFX failed for: {prompt}", e)
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
        for _ in range(random.randint(1, 2)):
            s_prompt = random.choice(sfx_prompts)
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

        return final_name
    except Exception as e:
        log_error(f"AudioCraft failed for: {prompt}", e)
        fallback_path = "sample_audio/fallback.mp3"
        if os.path.exists(fallback_path):
            import shutil, uuid
            new_file = f"{uuid.uuid4()}.mp3"
            shutil.copy(fallback_path, f"output_audio/{new_file}")
            return new_file
        else:
            raise HTTPException(status_code=500, detail="Audio generation and fallback both failed.")

@app.post("/generate-audio")
async def generate_audio(prompt: str = Form(...), duration: int = Form(...)):
    if duration not in {30, 60, 90, 120}:
        raise HTTPException(status_code=400, detail="Invalid duration. Must be 30, 60, 90, or 120 seconds")

    try:
        filename = generate_audio_from_text(prompt, duration)
    except Exception as e:
        log_error("generate-audio endpoint failed", e)
        raise HTTPException(status_code=500, detail="Audio generation failed. Check /diagnostic or error_log.txt.")
    status = "success"
    output_file = OUTPUT_DIR / filename

    # Append log
    with LOG_FILE.open("a") as logf:
        timestamp = datetime.utcnow().isoformat()
        logf.write(
            f"[{timestamp}] {prompt} | {filename} | {status}\n"
        )

    return JSONResponse({
        "file_url": f"/download/{filename}",
        "status": status,
    })

@app.get("/download/{filename}")
async def download(filename: str):
    file_path = OUTPUT_DIR / filename
    if not file_path.exists() or file_path.suffix != ".mp3":
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, media_type="audio/mpeg", filename=filename)


@app.get("/diagnostic")
def run_diagnostic():
    from os.path import exists
    checks = {
        "AudioCraft installed": False,
        "AudioLDM installed": False,
        "FFMPEG available": False,
        "output_audio folder": exists("output_audio"),
        "fallback file": exists("sample_audio/fallback.mp3"),
    }

    try:
        from audiocraft.models import musicgen
        model = musicgen.MusicGen.get_pretrained("small")
        checks["AudioCraft installed"] = True
    except:
        pass

    try:
        from audioldm import AudioLDM
        model = AudioLDM()
        checks["AudioLDM installed"] = True
    except:
        pass

    from shutil import which
    if which("ffmpeg"):
        checks["FFMPEG available"] = True

    return checks


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

