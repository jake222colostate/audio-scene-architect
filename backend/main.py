from fastapi import FastAPI, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from uuid import uuid4
from pathlib import Path
import random
import shutil
from datetime import datetime

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

@app.post("/generate-audio")
async def generate_audio(prompt: str = Form(...), duration: int = Form(...)):
    if duration not in {30, 60, 90, 120}:
        raise HTTPException(status_code=400, detail="Invalid duration. Must be 30, 60, 90, or 120 seconds")

    # Determine output file
    file_id = uuid4().hex
    output_file = OUTPUT_DIR / f"{file_id}.mp3"

    sample_files = list(SAMPLE_DIR.glob("*.mp3"))
    if sample_files:
        chosen = random.choice(sample_files)
        shutil.copy(chosen, output_file)
    else:
        # Write placeholder content
        output_file.write_bytes(b"FAKE_AUDIO_CONTENT")

    # Append log
    with LOG_FILE.open("a") as logf:
        timestamp = datetime.utcnow().isoformat()
        logf.write(f"{timestamp} | {prompt} | {duration} | {output_file.name}\n")

    return JSONResponse({"file_url": f"/download/{output_file.name}"})

@app.get("/download/{filename}")
async def download(filename: str):
    file_path = OUTPUT_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, media_type="audio/mpeg", filename=filename)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

