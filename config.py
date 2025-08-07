"""Configuration and constants for the application."""
import os
from pathlib import Path

# Directories
BASE_DIR = Path(__file__).parent
SAMPLE_DIR = BASE_DIR / "sample_audio"
OUTPUT_DIR = BASE_DIR / "output_audio"
UPLOAD_DIR = BASE_DIR / "uploads"
LOG_FILE = BASE_DIR / "audio_logs.txt"

REQUIRED_DIRS = ["output_audio", "sample_audio", "uploads", "audioldm/weights"]

# Ensure all required directories exist
for directory in REQUIRED_DIRS:
    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)

# Additional directory creation
SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# SFX Library
SFX_LIBRARY = {
    "fear": ["heavy breathing", "distant scream", "heartbeat"],
    "aggression": ["footsteps", "metal crash", "shouting"],
    "isolation": ["echoes", "dripping water", "creaking floor"],
    "neutral": ["soft wind", "low hum", "light static"],
}

# Predefined horror prompts for SFX generation
SFX_PROMPTS = [
    "distant whisper",
    "footsteps on old wood",
    "metal door slam",
    "wind howling through trees",
    "low breathing",
    "creaking floorboards",
]