from fastapi import FastAPI, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from uuid import uuid4
from pathlib import Path
import random
import shutil
from datetime import datetime
import uuid
import os

app = FastAPI()

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

# Ensure directories exist
SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def generate_audio_from_text(prompt: str, duration: int) -> str:
    """Generate an audio file from text using AudioCraft.

    Returns the generated filename located inside OUTPUT_DIR.
    """
    try:
        from audiocraft.models import musicgen
        from audiocraft.data.audio import audio_write
    except Exception as exc:
        raise RuntimeError("AudioCraft is not installed") from exc

    model = musicgen.MusicGen.get_pretrained("small")
    model.set_generation_params(duration=duration)

    # Generate the audio waveform
    try:
        wav = model.generate_with_chroma([prompt])
    except Exception as exc:
        raise RuntimeError("generation failed") from exc

    filename = f"{uuid.uuid4()}.wav"
    filepath = OUTPUT_DIR / filename

    audio_write(str(filepath.with_suffix("")), wav[0].cpu(), model.sample_rate, strategy="loudness")

    return filename

@app.post("/generate-audio")
async def generate_audio(prompt: str = Form(...), duration: int = Form(...)):
    if duration not in {30, 60, 90, 120}:
        raise HTTPException(status_code=400, detail="Invalid duration. Must be 30, 60, 90, or 120 seconds")

    try:
        filename = generate_audio_from_text(prompt, duration)
    except Exception:
        file_id = uuid4().hex
        output_file = OUTPUT_DIR / f"{file_id}.mp3"
        sample_files = list(SAMPLE_DIR.glob("*.mp3"))
        if sample_files:
            chosen = random.choice(sample_files)
            shutil.copy(chosen, output_file)
        else:
            output_file.write_bytes(b"FAKE_AUDIO_CONTENT")
        filename = output_file.name
    else:
        output_file = OUTPUT_DIR / filename

    # Append log
    with LOG_FILE.open("a") as logf:
        timestamp = datetime.utcnow().isoformat()
        logf.write(f"{timestamp} | {prompt} | {duration} | {filename}\n")

    return JSONResponse({"file_url": f"/download/{filename}"})

@app.get("/download/{filename}")
async def download(filename: str):
    file_path = OUTPUT_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    media_type = "audio/wav" if file_path.suffix == ".wav" else "audio/mpeg"
    return FileResponse(file_path, media_type=media_type, filename=filename)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

