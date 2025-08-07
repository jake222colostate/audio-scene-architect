"""Background job processing service."""
import time
import threading
import datetime
import traceback
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.logging import logger, log
from config import LOG_FILE

# Job tracking system
job_queue = []  # List of job dictionaries for easy manipulation
job_status = {}  # {filename: "queued"|"running"|"done"|"failed"|"canceled"}
processing_lock = threading.Lock()  # Thread safety for job queue

# Global semaphore for resource-aware request queuing
generation_lock = threading.Semaphore(1)

def process_jobs():
    """Background thread to process queued audio generation jobs."""
    # Import here to avoid circular imports
    from services.audio_generation import generate_audio_from_text
    
    logger.info("🚀 Threaded job processor started")
    while True:
        try:
            with processing_lock:
                if job_queue:
                    job = job_queue.pop(0)
                else:
                    job = None
            
            if job:
                job_id = job["id"]
                
                # Check for timeout (3 minutes)
                if time.time() - job["created_at"] > 180:
                    job_status[job_id] = "failed"
                    logger.error(f"[TIMEOUT] Job {job_id} exceeded max duration")
                    continue
                
                # Check if job was canceled
                if job_status.get(job_id) == "canceled":
                    logger.info(f"[CANCELED] Skipping canceled job: {job_id}")
                    continue
                
                # Mark as running and process
                job_status[job_id] = "running"
                logger.info(f"[PROCESSING] Starting job: {job_id}")
                
                try:
                    # Generate audio directly with original prompt (GPT-OSS enrichment moved to route handlers)
                    generate_audio_from_text(job['prompt'], job["duration"], job_id)
                    job_status[job_id] = "done"
                    logger.info(f"✅ File written to output_audio/{job_id}")
                    
                    # Write success to audio_logs.txt
                    with open("backend/audio_logs.txt", "a") as f:
                        timestamp = datetime.datetime.now().isoformat()
                        f.write(f"[{timestamp}] SUCCESS: {job['prompt']} | {job_id}\n")
                except Exception as e:
                    job_status[job_id] = "failed"
                    logger.error(f"[ERROR] Generation failed for {job_id}: {traceback.format_exc()}")
                    
                    # Write detailed error to audio_logs.txt
                    with open("backend/audio_logs.txt", "a") as f:
                        timestamp = datetime.datetime.now().isoformat()
                        f.write(f"[{timestamp}] GENERATION_FAILED: {job_id}\n")
                        f.write(f"Prompt: {job['prompt']}\n")
                        f.write(f"Duration: {job['duration']}\n")
                        f.write(f"Error: {traceback.format_exc()}\n\n")
            
            time.sleep(1)
            
        except Exception as e:
            logger.error(f"[ERROR] Job processor error: {traceback.format_exc()}")
            time.sleep(5)

def start_job_processor():
    """Start the background job processor thread."""
    print("🚀 Starting threaded job processor")
    threading.Thread(target=process_jobs, daemon=True).start()
    print("✅ FastAPI app loaded — waiting for requests...")