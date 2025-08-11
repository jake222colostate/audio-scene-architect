"""Audio generation and management routes."""
import os
import time
import uuid
import datetime
import traceback
import random
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from pydub import AudioSegment

from models.schemas import GenerateAudioRequest
from services.gpt_oss import query_gptoss
from services.job_processor import job_queue, job_status, processing_lock
from utils.logging import log_request, log, logger, log_fail
from config import OUTPUT_DIR, UPLOAD_DIR, SFX_LIBRARY

router = APIRouter(prefix="/api")

@router.post("/generate-audio")
async def generate_audio(data: GenerateAudioRequest):
    """Add audio generation request to queue with robust error handling and structured logging."""
    log_request(data.prompt, data.duration, "pending")
    
    try:
        # Validate duration
        if not (10 <= int(data.duration) <= 60):
            error_msg = f"Invalid duration: {data.duration}. Must be between 10 and 60 seconds"
            log.error(f"[API] {error_msg}")
            return JSONResponse(
                status_code=400,
                content={"error": error_msg, "trace": ""}
            )

        # Generate unique filename
        filename = f"{uuid.uuid4().hex}.mp3"
        log.info(f"[API] Generated filename: {filename}")
        
        # Enrich prompt with GPT-OSS (safe route handler call)
        enriched_prompt = query_gptoss(f"Rewrite this music and SFX prompt to be more cinematic and expressive: {data.prompt}")
        
        # Create job object and add to queue
        job = {
            "id": filename,
            "prompt": enriched_prompt,
            "duration": data.duration,
            "created_at": time.time()
        }
        
        # Add job to queue (thread-safe)
        with processing_lock:
            job_queue.append(job)
            job_status[filename] = "queued"
        
        log.info(f"[API] ✅ Job queued: {filename} (Queue size: {len(job_queue)})")
        
        # Log the request
        try:
            from config import LOG_FILE
            with open(LOG_FILE, "a") as logf:
                timestamp = datetime.datetime.now().isoformat()
                logf.write(f"[{timestamp}] REQUEST_QUEUED: {data.prompt} | {filename} | duration: {data.duration}\n")
        except Exception as e:
            log.warning(f"[API] Failed to write to log file: {e}")

        log.info(f"[API] Returning queued response for {filename}")
        return JSONResponse(
            {
                "message": "Audio generation queued",
                "filename": filename,
                "file_url": f"/audio/{filename}",
                "status": "queued",
                "queue_position": len(job_queue)
            }
        )
        
    except Exception as e:
        # Comprehensive error handling and logging
        error_msg = f"Audio generation queueing failed: {str(e)}"
        full_trace = traceback.format_exc()
        log_fail("api_request", error_msg)
        log.error(f"[API] {error_msg}\nFull traceback:\n{full_trace}")
        
        # Write to log file
        try:
            from config import LOG_FILE
            with open(LOG_FILE, "a") as logf:
                timestamp = datetime.datetime.now().isoformat()
                logf.write(f"[{timestamp}] API_ERROR: {data.prompt} | Error: {str(e)}\n")
                logf.write(f"Full traceback:\n{full_trace}\n")
        except Exception:
            pass  # Ignore log file errors in error handler
            
        return JSONResponse(
            status_code=500,
            content={
                "error": error_msg,
                "trace": full_trace if log.level <= 10 else ""  # Only show trace in debug mode
            }
        )

@router.get("/status/{filename}")
async def get_status(filename: str):
    """Check the status of an audio generation job."""
    if filename not in job_status:
        raise HTTPException(status_code=404, detail="Job not found")
    
    status = job_status[filename]
    file_path = OUTPUT_DIR / filename
    file_exists = file_path.exists()
    
    # If file is done, check if it actually exists
    if status == "done":
        if not file_exists:
            job_status[filename] = "failed"
            status = "failed"
    
    return {
        "status": "complete" if status == "done" and file_exists else status,
        "filename": filename,
        "file_exists": file_exists,
        "file_url": f"/audio/{filename}" if file_exists else None
    }

@router.get("/download/{filename}")
async def download_file(filename: str):
    """Download generated audio file."""
    file_path = OUTPUT_DIR / filename
    
    if not file_path.exists():
        # Check if it's still being processed
        if filename in job_status and job_status[filename] in ["queued", "running"]:
            raise HTTPException(status_code=202, detail="File is still being processed")
        else:
            raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="audio/mpeg"
    )

@router.post("/upload-video")
async def upload_video(file: UploadFile = File(...)):
    """Upload video file for SFX generation."""
    if not file.filename.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
        raise HTTPException(status_code=400, detail="Invalid video format")
    
    # Save uploaded file
    video_id = f"{uuid.uuid4().hex}.mp4"
    video_path = UPLOAD_DIR / video_id
    
    with open(video_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
    
    return {"video_id": video_id, "message": "Video uploaded successfully"}

@router.post("/generate-sfx-from-video/{video_id}")
async def sfx_from_video(video_id: str):
    """Generate a short SFX track from an uploaded video."""
    # Import here to avoid circular imports
    from services.audio_generation import transcribe_video, analyze_tone, generate_sfx_clip
    
    path = UPLOAD_DIR / video_id
    if not path.exists():
        raise HTTPException(status_code=404, detail="Video not found")

    transcript = transcribe_video(str(path))
    
    # Use GPT-OSS for tone extraction and scene prompt generation
    scene_prompt = query_gptoss(f"Based on this transcript, write a cinematic audio prompt that fits the mood:\n\n{transcript}")
    logger.info(f"[VIDEO-SFX] GPT-OSS generated scene prompt: {scene_prompt}")
    
    # Fallback to traditional tone analysis if GPT-OSS fails
    tone = analyze_tone(transcript)
    sfx_prompts = [scene_prompt] if scene_prompt != transcript else random.sample(SFX_LIBRARY[tone], 2)

    clips = [generate_sfx_clip(p, 10) for p in sfx_prompts]
    combined = AudioSegment.silent(duration=10000)
    for clip in clips:
        if clip and os.path.exists(clip):
            audio = AudioSegment.from_file(clip)
            combined = combined.overlay(audio)

    # Export final track
    output_filename = f"sfx_{video_id}.mp3"
    output_path = OUTPUT_DIR / output_filename
    combined.export(str(output_path), format="mp3")

    return {
        "transcript": transcript,
        "sfx_file": output_filename,
        "download_url": f"/api/download/{output_filename}"
    }

@router.post("/enrich")
async def enrich_prompt(data: dict):
    """Enrich a prompt using GPT-OSS for more cinematic and descriptive audio generation."""
    try:
        prompt = data.get("prompt", "")
        if not prompt:
            raise HTTPException(status_code=400, detail="Prompt is required")
        
        logger.info(f"[ENRICH] Enriching prompt via API: '{prompt[:50]}{'...' if len(prompt) > 50 else ''}'")
        
        enriched = query_gptoss(f"Make this audio prompt more descriptive and cinematic: {prompt}")
        
        logger.info(f"[ENRICH] API enrichment completed")
        
        return {
            "original": prompt,
            "enriched": enriched,
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"[ENRICH] Error during prompt enrichment: {str(e)}")
        return {
            "original": prompt,
            "enriched": prompt,  # Fallback to original
            "status": "error",
            "error": str(e)
        }

@router.get("/debug/test-audio")
async def test_audio_generation():
    """Test endpoint to verify audio generation is working."""
    try:
        # Import here to avoid circular imports
        from services.audio_generation import generate_audio_from_text
        
        # Generate a simple test audio
        test_filename = f"test_{uuid.uuid4().hex[:8]}.mp3"
        test_prompt = "gentle piano melody"
        
        logger.info(f"[TEST] Generating test audio: {test_filename}")
        
        # Generate 5-second test audio
        generate_audio_from_text(test_prompt, 5, test_filename)
        
        file_path = OUTPUT_DIR / test_filename
        if file_path.exists():
            return {
                "status": "success",
                "message": "Test audio generated successfully",
                "filename": test_filename,
                "file_url": f"/audio/{test_filename}",
                "file_size": file_path.stat().st_size
            }
        else:
            return {
                "status": "error",
                "message": "Test audio file was not created"
            }
            
    except Exception as e:
        logger.error(f"[TEST] Test audio generation failed: {traceback.format_exc()}")
        return {
            "status": "error",
            "message": f"Test failed: {str(e)}",
            "trace": traceback.format_exc()
        }