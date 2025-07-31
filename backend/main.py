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
import logging
from pydub import AudioSegment


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
SOUND_LAYER_DIR = BASE_DIR / "sound_layers"
LOG_FILE = BASE_DIR / "audio_logs.txt"

# Ensure directories exist
SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
SOUND_LAYER_DIR.mkdir(parents=True, exist_ok=True)


def apply_sound_layers(base_audio: AudioSegment):
    """Randomly overlay 1-2 ambient layers onto the base audio."""
    overlays_used = []
    candidates = list(SOUND_LAYER_DIR.glob("*.mp3"))
    if candidates:
        num_layers = random.randint(1, min(2, len(candidates)))
        for layer_path in random.sample(candidates, num_layers):
            try:
                overlay = AudioSegment.from_file(layer_path)
            except Exception:
                continue
            overlay = overlay - random.randint(6, 12)
            start_ms = random.randint(0, max(0, len(base_audio) - len(overlay)))
            base_audio = base_audio.overlay(overlay, position=start_ms)
            overlays_used.append(layer_path.name)
    return base_audio, overlays_used


def generate_audio_from_text(prompt: str, duration: int):
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

    # Convert wav to mp3
    mp3_filename = filepath.with_suffix(".mp3").name
    mp3_path = OUTPUT_DIR / mp3_filename
    AudioSegment.from_wav(filepath).export(mp3_path, format="mp3")
    os.remove(filepath)

    base_audio = AudioSegment.from_mp3(mp3_path)
    base_audio, overlays = apply_sound_layers(base_audio)
    base_audio.export(mp3_path, format="mp3")

    return mp3_filename, overlays

@app.post("/generate-audio")
async def generate_audio(prompt: str = Form(...), duration: int = Form(...)):
    if duration not in {30, 60, 90, 120}:
        raise HTTPException(status_code=400, detail="Invalid duration. Must be 30, 60, 90, or 120 seconds")

    try:
        filename, overlays = generate_audio_from_text(prompt, duration)
        status = "success"
    except Exception as exc:
        logging.error("Audio generation failed: %s", exc)
        file_id = uuid4().hex
        output_file = OUTPUT_DIR / f"{file_id}.mp3"
        fallback = SAMPLE_DIR / "fallback.mp3"
        if not fallback.exists():
            sample_files = list(SAMPLE_DIR.glob("*.mp3"))
            fallback = random.choice(sample_files) if sample_files else None
        if fallback and fallback.exists():
            shutil.copy(fallback, output_file)
        else:
            output_file.write_bytes(b"FAKE_AUDIO_CONTENT")
        base = AudioSegment.from_mp3(output_file)
        base, overlays = apply_sound_layers(base)
        base.export(output_file, format="mp3")
        filename = output_file.name
        status = "fallback"
    else:
        output_file = OUTPUT_DIR / filename

    # Append log
    with LOG_FILE.open("a") as logf:
        timestamp = datetime.utcnow().isoformat()
        overlay_str = ",".join(overlays) if overlays else "none"
        logf.write(
            f"[{timestamp}] {prompt} | {duration} | {filename} | {overlay_str} | {status}\n"
        )

    return JSONResponse({
        "file_url": f"/download/{filename}",
        "duration": duration,
        "status": status,
    })

@app.get("/download/{filename}")
async def download(filename: str):
    file_path = OUTPUT_DIR / filename
    if not file_path.exists() or file_path.suffix != ".mp3":
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, media_type="audio/mpeg", filename=filename)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

