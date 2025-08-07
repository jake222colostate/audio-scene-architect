#!/usr/bin/env python3
"""
Simplified script to run the FastAPI backend with better error handling.
"""

import sys
import os
import logging
from pathlib import Path

# Add current directory to Python path
sys.path.append(str(Path(__file__).parent))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def check_dependencies():
    """Check if all required dependencies are available."""
    missing = []
    
    try:
        import fastapi
        logging.info("✓ FastAPI available")
    except ImportError:
        missing.append("fastapi")
    
    try:
        import uvicorn
        logging.info("✓ Uvicorn available")
    except ImportError:
        missing.append("uvicorn")
    
    try:
        import torch
        import torchaudio
        logging.info("✓ PyTorch and torchaudio available")
    except ImportError:
        missing.append("torch/torchaudio")
    
    try:
        from audiocraft.models import musicgen
        logging.info("✓ AudioCraft available")
    except ImportError:
        missing.append("audiocraft")
    
    try:
        from audioldm import AudioLDM
        logging.info("✓ AudioLDM available")
    except ImportError:
        missing.append("audioldm")
    
    try:
        from pydub import AudioSegment
        logging.info("✓ pydub available")
    except ImportError:
        missing.append("pydub")
    
    try:
        import psutil
        logging.info("✓ psutil available")
    except ImportError:
        missing.append("psutil")
    
    from shutil import which
    if which("ffmpeg"):
        logging.info("✓ ffmpeg available")
    else:
        missing.append("ffmpeg")
    
    return missing

def main():
    """Main function to run the FastAPI server."""
    logging.info("Starting SoundForge.AI Backend...")
    
    # Check dependencies
    missing = check_dependencies()
    if missing:
        logging.error(f"Missing dependencies: {', '.join(missing)}")
        logging.error("Please install missing dependencies and try again.")
        return 1
    
    # Ensure required directories exist
    required_dirs = ["output_audio", "sample_audio", "uploads"]
    for directory in required_dirs:
        os.makedirs(directory, exist_ok=True)
        logging.info(f"✓ Directory ensured: {directory}")
    
    # Import and run the FastAPI app
    try:
        import uvicorn
        from main import app
        
        logging.info("Starting FastAPI server on http://localhost:8000")
        logging.info("API will be available at:")
        logging.info("  - POST /generate-audio")
        logging.info("  - GET /diagnostic")
        logging.info("  - GET /download/{filename}")
        
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            log_level="info",
            reload=False  # Disable reload for production
        )
        
    except Exception as e:
        logging.error(f"Failed to start server: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())